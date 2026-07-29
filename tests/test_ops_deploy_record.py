"""Tests for the Deploy-of-Record InstalledSet grammar."""

from __future__ import annotations

import json

import pytest

from vpath_platform_mgmt.ops import deploy_record as record
from vpath_platform_mgmt.ops.deploy_record import InstalledSetError

VALID = json.dumps({"schema_version": 1, "apps": ["vpath-web"], "workflows": []})


def test_parse_accepts_a_well_formed_set() -> None:
    data = record.parse(VALID)
    assert data["apps"] == ["vpath-web"]
    assert data["workflows"] == []


def test_parse_rejects_invalid_json() -> None:
    with pytest.raises(InstalledSetError, match="not valid JSON"):
        record.parse("{nope")


def test_parse_rejects_a_non_object_document() -> None:
    with pytest.raises(InstalledSetError, match="top level is not an object"):
        record.parse("[]")


def test_parse_rejects_an_unsupported_schema_version() -> None:
    body = json.dumps({"schema_version": 2, "apps": [], "workflows": []})
    with pytest.raises(InstalledSetError, match="schema_version"):
        record.parse(body)


def test_parse_rejects_a_missing_array() -> None:
    body = json.dumps({"schema_version": 1, "apps": []})
    with pytest.raises(InstalledSetError, match="'workflows' is not an array"):
        record.parse(body)


def test_parse_rejects_a_non_string_entry() -> None:
    body = json.dumps({"schema_version": 1, "apps": [7], "workflows": []})
    with pytest.raises(InstalledSetError, match="non-string"):
        record.parse(body)


def test_parse_rejects_duplicates() -> None:
    body = json.dumps({"schema_version": 1, "apps": ["a", "a"], "workflows": []})
    with pytest.raises(InstalledSetError, match="duplicates"):
        record.parse(body)


def test_parse_rejects_a_name_the_engine_would_reject() -> None:
    body = json.dumps({"schema_version": 1, "apps": ["Bad_Name"], "workflows": []})
    with pytest.raises(InstalledSetError, match="invalid template name"):
        record.parse(body)


def test_add_is_sorted_and_idempotent() -> None:
    data = record.parse(VALID)
    once = record.add(data, "app", "alpha")
    twice = record.add(once, "app", "alpha")
    assert once["apps"] == ["alpha", "vpath-web"]
    assert twice["apps"] == once["apps"]


def test_add_does_not_mutate_the_original() -> None:
    data = record.parse(VALID)
    record.add(data, "app", "alpha")
    assert data["apps"] == ["vpath-web"]


def test_remove_drops_only_the_named_template() -> None:
    data = record.parse(VALID)
    assert record.remove(data, "app", "vpath-web")["apps"] == []
    assert record.remove(data, "app", "absent")["apps"] == ["vpath-web"]


def test_contains_reports_membership() -> None:
    data = record.parse(VALID)
    assert record.contains(data, "app", "vpath-web")
    assert not record.contains(data, "app", "other")


def test_dump_round_trips_through_parse() -> None:
    data = record.parse(VALID)
    assert record.parse(record.dump(data)) == data


def test_dump_ends_with_a_newline() -> None:
    assert record.dump(record.parse(VALID)).endswith("\n")


def test_array_for_rejects_an_unknown_kind() -> None:
    with pytest.raises(InstalledSetError, match="invalid template kind"):
        record.array_for("chart")


def test_paths_match_the_engine_layout() -> None:
    assert record.payload_path("app", "demo") == "apps/demo"
    assert record.payload_path("workflow", "demo") == "workflows/demo"
    assert record.appset_input_path("demo") == "appset-inputs/demo.json"


def test_paths_refuse_a_traversal_name() -> None:
    with pytest.raises(InstalledSetError, match="invalid template name"):
        record.payload_path("app", "../etc")
