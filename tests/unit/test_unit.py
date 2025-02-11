"""Tests specific to the unit test functionality."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_ansible.units import inject, inject_only


def test_inject(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test injecting a path.

    :param monkeypatch: The pytest monkeypatch fixture
    :param tmp_path: The pytest tmp_path fixture
    :param caplog: The pytest caplog fixture
    """
    caplog.set_level(logging.DEBUG)

    def mock_get_collection_name(start_path: str) -> tuple[str, str]:
        """Mock the get_collection_name function.

        :param start_path: The path to the root of the collection
        :returns: A tuple of the namespace and name
        """
        return "namespace", "name"

    monkeypatch.setattr(
        "pytest_ansible.units.get_collection_name",
        mock_get_collection_name,
    )

    (tmp_path / "collections" / "ansible_collections").mkdir(parents=True)

    inject(tmp_path)
    assert (
        tmp_path / "collections" / "ansible_collections" / "namespace" / "name"
    ).is_dir()
    assert (
        str(tmp_path / "collections")
        == sys.path[0]
        == re.search(r"_ACF installed: \['(.*?)'.*]", caplog.text).groups()[0]
        == re.search(r"_ACF configured paths: \['(.*?)'.*]", caplog.text).groups()[0]
    )


def test_inject_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test only injecting a path.

    :param monkeypatch: The pytest monkeypatch fixture
    :param tmp_path: The pytest tmp_path fixture
    :param caplog: The pytest caplog fixture
    """
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("ANSIBLE_COLLECTIONS_PATH", str(tmp_path / "collections"))

    (tmp_path / "collections" / "ansible_collections").mkdir(parents=True)

    inject_only()
    assert (
        str(tmp_path / "collections")
        == sys.path[0]
        == re.search(r"_ACF installed: \['(.*?)'.*]", caplog.text).groups()[0]
        == re.search(r"_ACF configured paths: \['(.*?)'.*]", caplog.text).groups()[0]
    )


def test_for_params():
    """Test for params."""
    proc = subprocess.run("pytest --help", shell=True, capture_output=True, check=False)
    assert "--ansible-unit-inject-only" in proc.stdout.decode()
