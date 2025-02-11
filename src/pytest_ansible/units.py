"""Setup the collection for testing."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    HAS_ANSIBLE = True
except ImportError:
    HAS_ANSIBLE = False

try:
    from ansible.utils.collection_loader._collection_finder import (
        _AnsibleCollectionFinder,
    )

    HAS_COLLECTION_FINDER = True
except ImportError:
    HAS_COLLECTION_FINDER = False


def get_collection_name(start_path: Path) -> tuple[str | None, str | None]:
    """Get the collection namespace and name from the galaxy.yml file.

    :param start_path: The path to the root of the collection
    :returns: A tuple of the namespace and name
    """
    info_file = start_path / "galaxy.yml"
    logger.info("Looking for collection info in %s", info_file)

    try:
        with info_file.open(encoding="utf-8") as fhand:
            galaxy_info = yaml.safe_load(fhand)
    except FileNotFoundError:
        logger.error("No galaxy.yml file found, plugin not activated")
        return None, None

    try:
        namespace = galaxy_info["namespace"]
        name = galaxy_info["name"]
    except KeyError:
        logger.error("galaxy.yml file does not contain namespace and name")
        return None, None

    logger.debug("galaxy.yml file found, plugin activated")
    logger.info("Collection namespace: %s", namespace)
    logger.info("Collection name: %s", name)
    return namespace, name


def inject(start_path: Path) -> None:
    """Inject the collection path.

    In the case of ansible > 2.9, initialize the collection finder with the collection path
    otherwise, inject the collection path into sys.path.

    :param start_path: The path where pytest was invoked
    """
    if not HAS_ANSIBLE:
        logger.error("ansible is not installed, plugin not activated")
        return
    if not HAS_YAML:
        logger.error("pyyaml is not installed, plugin not activated")
        return

    logger.debug("Start path: %s", start_path)
    namespace, name = get_collection_name(start_path)
    if namespace is None or name is None:
        # Tests may not being run from the root of the repo.
        return

    # Determine if the start_path is in a collections tree
    collection_tree = ("collections", "ansible_collections", namespace, name)
    if start_path.parts[-4:] == collection_tree:
        logger.info("In collection tree")
        collections_dir = start_path.parents[2]

    else:
        logger.info("Not in collection tree")
        collections_dir = start_path / "collections"
        name_dir = collections_dir / "ansible_collections" / namespace / name

        # If it's here, we will trust it was from this
        if not name_dir.is_dir():
            os.makedirs(name_dir, exist_ok=True)

            for entry in start_path.iterdir():
                if entry.name == "collections":
                    continue
                os.symlink(entry, name_dir / entry.name)

    logger.info("Collections dir: %s", collections_dir)

    # TODO: Make this a configuration option, check COLLECTIONS_PATH
    # Add the user location for any dependencies
    paths = [str(collections_dir), "~/.ansible/collections"]
    logger.info("Paths: %s", paths)

    acf_inject(paths=paths)

    # Inject the path for the collection into sys.path
    # This is needed for import udring mock tests
    sys.path.insert(0, str(collections_dir))
    logger.debug("sys.path updated: %s", sys.path)

    # TODO: Should we install any collection dependencies as well?
    # or let the developer do that?
    # e.g. ansible-galaxy collection install etc

    # Set the environment variable as courtesy for integration tests

    envvar_name = determine_envvar()
    env_paths = os.pathsep.join(paths)
    logger.info("Setting %s to %s", envvar_name, env_paths)
    os.environ[envvar_name] = env_paths


def inject_only() -> None:
    """Inject the current ANSIBLE_COLLECTIONS_PATH(S)."""
    envvar_name = determine_envvar()
    env_paths = os.environ.get(envvar_name, "")
    path_list = env_paths.split(os.pathsep)
    for path in path_list:
        if path:
            sys.path.insert(0, path)
    logger.debug("sys.path updated: %s", sys.path)
    acf_inject(paths=path_list)


def acf_inject(paths: list[str]) -> None:
    """Inject the collection path into the AnsibleCollectionFinder.

    :param paths: The paths to inject
    """
    # pylint: disable=protected-access
    if HAS_COLLECTION_FINDER:
        acf = _AnsibleCollectionFinder(paths=paths)
        acf._install()
        logger.debug("_ACF installed: %s", paths)
        logger.debug("_ACF configured paths: %s", acf._n_configured_paths)
    else:
        logger.debug("_ACF not available")


def determine_envvar() -> str:
    """Use the existence of the AnsibleCollectionFinder to determine
    the ansible version.

    ansible 2.9 did not have AnsibleCollectionFinder and did not support ANSIBLE_COLLECTIONS_PATH
    later versions do.

    :returns: The appropriate environment variable to use
    """
    if not HAS_COLLECTION_FINDER:
        return "ANSIBLE_COLLECTIONS_PATHS"
    return "ANSIBLE_COLLECTIONS_PATH"
