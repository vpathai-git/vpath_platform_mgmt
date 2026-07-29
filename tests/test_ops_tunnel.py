"""Tests for the one process this application ever starts."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.ops import tunnel
from vpath_platform_mgmt.ops.tunnel import (
    ALREADY_UP,
    STARTED,
    TunnelConfig,
    TunnelError,
)

ENV = {
    "VPATH_MGMT_SSH_HOST": "20.86.32.146",
    "VPATH_MGMT_SSH_USER": "azureuser",
    "VPATH_MGMT_SSH_KEY": "/keys/vm5.pem",
}


class FakeProcess:
    """An ssh that either stays up or dies with a message."""

    def __init__(self, stderr: str = "", alive: bool = True) -> None:
        self._alive = alive
        self.returncode = 0 if alive else 255
        self.stderr = None if alive else _Reader(stderr)
        self.terminated = False

    def poll(self) -> int | None:
        return None if self._alive else self.returncode

    def terminate(self) -> None:
        self.terminated = True


class _Reader:
    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text


def _config(key: Path) -> TunnelConfig:
    return TunnelConfig(host="h", user="u", key=str(key), port=1085)


def test_from_env_names_every_missing_field() -> None:
    with pytest.raises(TunnelError, match="VPATH_MGMT_SSH_HOST") as missing:
        tunnel.from_env({})
    assert "VPATH_MGMT_SSH_USER" in str(missing.value)
    assert "VPATH_MGMT_SSH_KEY" in str(missing.value)


def test_from_env_defaults_the_port_and_rejects_a_bad_one() -> None:
    assert tunnel.from_env(ENV).port == tunnel.DEFAULT_SOCKS_PORT
    assert tunnel.from_env({**ENV, "VPATH_MGMT_TUNNEL_PORT": "2000"}).port == 2000
    with pytest.raises(TunnelError, match="not a port number"):
        tunnel.from_env({**ENV, "VPATH_MGMT_TUNNEL_PORT": "eleven"})


def test_argv_carries_no_caller_input_and_cannot_prompt() -> None:
    """The console spawns this; nothing in it may come from a request."""
    argv = tunnel.from_env(ENV).argv()
    assert argv[0] == "ssh"
    assert "-D" in argv and "127.0.0.1:1085" in argv
    assert "BatchMode=yes" in argv  # a key prompt would hang the request
    assert "azureuser@20.86.32.146" in argv
    assert not any(";" in part or "&&" in part for part in argv)


def test_an_existing_tunnel_is_reported_never_replaced(tmp_path: Path) -> None:
    """Rebinding the port would break the tunnel that already works."""
    spawned: list[list[str]] = []
    result = tunnel.start(
        _config(tmp_path / "k.pem"),
        spawn=lambda argv: spawned.append(argv),  # type: ignore[arg-type,return-value]
        listening=lambda _port: True,
    )
    assert result == ALREADY_UP
    assert spawned == []


def test_a_missing_key_fails_before_spawning_anything(tmp_path: Path) -> None:
    with pytest.raises(TunnelError, match="SSH key not found"):
        tunnel.start(
            _config(tmp_path / "absent.pem"),
            spawn=lambda argv: FakeProcess(),  # type: ignore[arg-type,return-value]
            listening=lambda _port: False,
        )


def test_start_waits_for_the_port_to_open(tmp_path: Path) -> None:
    key = tmp_path / "k.pem"
    key.write_text("key", encoding="utf-8")
    checks = iter([False, False, True])
    result = tunnel.start(
        _config(key),
        spawn=lambda argv: FakeProcess(),  # type: ignore[arg-type,return-value]
        listening=lambda _port: next(checks),
        sleep=lambda _s: None,
    )
    assert result == STARTED


def test_ssh_dying_reports_its_own_last_line(tmp_path: Path) -> None:
    """The operator needs ssh's reason, not our exit code."""
    key = tmp_path / "k.pem"
    key.write_text("key", encoding="utf-8")
    dead = FakeProcess(stderr="Permission denied (publickey).", alive=False)
    with pytest.raises(TunnelError, match="Permission denied"):
        tunnel.start(
            _config(key),
            spawn=lambda argv: dead,  # type: ignore[arg-type,return-value]
            listening=lambda _port: False,
            sleep=lambda _s: None,
        )


def test_a_tunnel_that_never_opens_is_terminated(tmp_path: Path) -> None:
    key = tmp_path / "k.pem"
    key.write_text("key", encoding="utf-8")
    hung = FakeProcess()
    with pytest.raises(TunnelError, match="did not open"):
        tunnel.start(
            _config(key),
            spawn=lambda argv: hung,  # type: ignore[arg-type,return-value]
            listening=lambda _port: False,
            sleep=lambda _s: None,
        )
    assert hung.terminated is True  # no orphaned ssh left behind
