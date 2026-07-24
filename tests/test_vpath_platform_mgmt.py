"""Tests for the placeholder package (replace as real code lands)."""

import pytest

from vpath_platform_mgmt import __version__, hello, main


def test_hello_returns_greeting() -> None:
    assert hello() == "hello from vpath_platform_mgmt"


def test_main_prints_greeting(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    assert "hello from vpath_platform_mgmt" in capsys.readouterr().out


def test_version_is_semver() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
