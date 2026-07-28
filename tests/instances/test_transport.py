"""The transport's refusals -- the guard in front of every remote command.

`require_ssh` is the last thing between a typed instance name and a command
running on somebody's machine. Its refusals are guards, so each one is tested
by the message it gives as well as the fact that it raises: an operator who is
told the wrong reason looks in the wrong place.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vpath_platform_mgmt.instances.instance import Instance
from vpath_platform_mgmt.instances.transport import TransportError, require_ssh


def instance(kind: str, **fields: str) -> Instance:
    return Instance(
        name="target",
        kind=kind,
        lifecycle="live",
        fields=fields,
        source="test-register",
    )


def test_a_server_with_coordinates_is_allowed() -> None:
    require_ssh(instance("server-nuc", SSH_HOST="10.0.0.1", SSH_USER="boxuser"))


def test_a_customer_cluster_is_refused_for_want_of_clearance() -> None:
    """The survey established HOW to reach one -- not that we may.

    This is the one refusal that must not soften when the access path becomes
    known, so it is pinned to the reason rather than to the raise.
    """
    with pytest.raises(TransportError) as refused:
        require_ssh(instance("remote", CLUSTER_HOST="cluster.example"))

    message = str(refused.value)
    assert "no clearance" in message
    assert "CONSOLE_PERMITTED" in message
    assert "remote-type-survey" in message


def test_a_standalone_is_refused_as_a_local_process_not_as_unclear() -> None:
    """A different reason from the remote one, and it has to stay different."""
    with pytest.raises(TransportError) as refused:
        require_ssh(instance("standalone", APP_ROOT="/app", HOME="/home"))

    message = str(refused.value)
    assert "local process" in message
    assert "clearance" not in message


def test_a_planned_instance_is_refused_because_it_does_not_exist_yet() -> None:
    planned = Instance(
        name="mars",
        kind="server-nuc",
        lifecycle="planned",
        fields={},
        source="test-register",
    )

    with pytest.raises(TransportError, match="does not exist yet"):
        require_ssh(planned)


def test_a_missing_key_names_where_to_get_it(tmp_path: Path) -> None:
    """The refusal has to say what to extract, not just that something is gone."""
    absent = tmp_path / "nokey"

    with pytest.raises(TransportError) as refused:
        require_ssh(
            instance(
                "server-cloud-vm",
                SSH_HOST="203.0.113.7",
                SSH_USER="cloud",
                SSH_KEY=str(absent),
                SSH_KEY_SOURCE="bundle.zip::key.pem",
            )
        )

    assert "bundle.zip::key.pem" in str(refused.value)
