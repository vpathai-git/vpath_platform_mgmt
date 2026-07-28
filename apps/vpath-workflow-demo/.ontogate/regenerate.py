#!/usr/bin/env python3
"""Regenerate ontology.json from spine.yaml for the app's OntoGate gate.

Stdlib-only — the Spine-3 catalog is a small flat file, so a tiny reader
suffices. Stamps the provenance the vendored gatelib M10 freshness guard reads
(generated_from / source_sha256 / generated_with). Run after editing spine.yaml:

    python3 examples/vpath-workflow-demo/.ontogate/regenerate.py

A stale ontology.json (spine edited without regenerating) makes check.py exit 2.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT_ROOT = HERE.parents[2]
sys.path.insert(0, str(KIT_ROOT / "foundation"))  # the foundation `audit` pkg
from audit.helpers import _mini_yaml  # noqa: E402

_VENDORED_ONTOGATE_VERSION = "0.10.44"  # matches foundation/_vendor/gatelib/


def _entities(data):
    """Normalize the spine's entity catalog: the mini-yaml reader has no
    lists, so `deps` is authored as a comma-separated scalar — split it here.
    Dropping this carry-through would silently disable the whole concept
    plane (R-A..R-E see an empty catalog), so it is as load-bearing as the
    `unguarded` carry below."""
    out = {}
    for name, ent in (data.get("entities") or {}).items():
        e = dict(ent)
        deps = e.get("deps", "")
        if isinstance(deps, str):
            e["deps"] = [d.strip() for d in deps.split(",") if d.strip()]
        out[name] = e
    return out


def _unquote(value):
    """Strip one matched pair of surrounding quotes from a mini-yaml scalar."""
    if (
        isinstance(value, str)
        and len(value) > 1
        and value[0] == value[-1]
        and value[0] in "\"'"
    ):
        return value[1:-1]
    return value


def _requirement_seam(data):
    """Carry the top-level `requirement_seam` block (M13/SEAM) to the gate.

    Two reasons this needs a helper rather than a bare `data.get(...)`: the
    mini-yaml reader keeps the surrounding quotes on a scalar, and the
    `decision:` pointer MUST be quoted in the spine (` :: ` is not expressible
    as a plain YAML scalar), so the quotes are stripped here — the SEAM row
    reads `decision` as a real `<file> :: <anchor>` pointer. An absent block is
    carried through as `None`, never as a `{}` default: a removed declaration
    must reach the gate as SEAM@spine:undeclared, not as a shim-invented empty
    one. Dropping this carry-through would silently disable the SEAM row.
    """
    block = data.get("requirement_seam")
    if not isinstance(block, dict):
        return block
    return {k: _unquote(v) for k, v in block.items()}


def main():
    src = HERE / "spine.yaml"
    data = _mini_yaml(src.read_text(encoding="utf-8"))
    model = data.get("model", {})
    ont = {
        "model": {
            "name": model.get("name"),
            "layer": model.get("layer"),
            "version": model.get("version"),
            "extension_procedure": model.get("extension_procedure"),
            "method_version": model.get("method_version"),
            "generated_from": "spine.yaml",
            "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "generated_with": _VENDORED_ONTOGATE_VERSION,
        },
        "contracts": data.get("contracts", {}),
        "fill": data.get("fill", {}),
        "need": data.get("need", {}),
        # UNG channel: carry an `unguarded:` block through to the gate. Without
        # this line a spine-authored declaration would be silently dropped and
        # the UNG row would keep saying "none declared" — the gate validates
        # the carried shape and fails loud on a malformed one.
        "unguarded": data.get("unguarded", {}),
        # SEAM channel (M13): the requirement-seam declaration, carried
        # verbatim (quotes stripped) so requirement_seam_row can verify it.
        "requirement_seam": _requirement_seam(data),
        # Concept plane (R-A..R-E): the app-domain catalog + the R-D
        # permission pins, carried from the spine's [app-catalog] section.
        "entities": _entities(data),
        "concept_pins": data.get("concept_pins", {}) or {},
    }
    out = HERE / "ontology.json"
    out.write_text(
        json.dumps(ont, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"regenerated {out.name}: {len(ont['contracts'])} contracts")


if __name__ == "__main__":
    main()
