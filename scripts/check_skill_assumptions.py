#!/usr/bin/env python3
"""Validate dated assumption blocks carried by vendored files.

Targets: the fable-team food-chain block in
.claude/skills/fable-team/SKILL.md (is the model tier map still
current?) and the review stamp in CLAUDE.md (do the project rules still
match reality?). This script CANNOT know the current model lineup or
read the team's mind; it only verifies each block parses and is not
past its review horizon — a human or current-session agent does the
actual revalidation.

Exit codes (worst across targets; all targets always reported):
  0 = fresh (or file not present - stated, never silent)
  1 = stale, revalidation recommended (not an error; cf. sync script)
  2 = an assumptions block is missing or malformed - contract broken
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SKILL_REL_PATH = Path(".claude") / "skills" / "fable-team" / "SKILL.md"
SENTINEL_BEGIN = "<!-- FOOD-CHAIN-ASSUMPTIONS-BEGIN -->"
SENTINEL_END = "<!-- FOOD-CHAIN-ASSUMPTIONS-END -->"
CLAUDE_MD_REL_PATH = Path("CLAUDE.md")
AGENTS_MD_REL_PATH = Path("AGENTS.md")
CLAUDE_MD_BEGIN = "<!-- CLAUDE-MD-ASSUMPTIONS-BEGIN -->"
CLAUDE_MD_END = "<!-- CLAUDE-MD-ASSUMPTIONS-END -->"
CONTEXT_DECAY_BEGIN = "<!-- CONTEXT-DECAY-ASSUMPTIONS-BEGIN -->"
CONTEXT_DECAY_END = "<!-- CONTEXT-DECAY-ASSUMPTIONS-END -->"
REQUIRED_KEYS = ("validated", "review_horizon_days")


@dataclass(frozen=True)
class Target:
    rel_path: Path
    begin: str
    end: str
    label: str
    banner_title: str
    review_hint: str
    claude_md_checks: bool = False
    optional: bool = False


TARGETS = (
    Target(
        SKILL_REL_PATH,
        SENTINEL_BEGIN,
        SENTINEL_END,
        "fable-team skill",
        "FOOD-CHAIN REVALIDATION DUE",
        "is 'fable' still the top tier? Do new Agent model values exist?\n"
        "Update the tier map if the food chain changed",
    ),
    Target(
        CLAUDE_MD_REL_PATH,
        CLAUDE_MD_BEGIN,
        CLAUDE_MD_END,
        "CLAUDE.md",
        "CLAUDE.MD REVALIDATION DUE",
        "do the hard rules, skills roster and Must-Know Map still match\n"
        "reality? Propose edits for human approval if not",
        claude_md_checks=True,
    ),
    Target(
        CLAUDE_MD_REL_PATH,
        CONTEXT_DECAY_BEGIN,
        CONTEXT_DECAY_END,
        "context-decay rule",
        "CONTEXT-DECAY REVALIDATION DUE",
        "do the compaction bands still hold for the current model? re-check\n"
        "Anthropic context-rot guidance + long-context benchmarks, re-stamp",
        optional=True,
    ),
)


def extract_block(text: str, target: Target, path: Path) -> dict[str, str]:
    if text.count(target.begin) != 1 or text.count(target.end) != 1:
        raise ValueError(
            f"{path}: expected exactly one {target.begin} / {target.end} "
            "sentinel pair"
        )
    inner = text.split(target.begin, 1)[1].split(target.end, 1)[0]
    pairs: dict[str, str] = {}
    for line in inner.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}: unparseable line in assumptions block: {line!r}")
        key, value = line.split(":", 1)
        pairs[key.strip()] = value.strip()
    for key in REQUIRED_KEYS:
        if key not in pairs:
            raise ValueError(f"{path}: assumptions block missing required key '{key}'")
    return pairs


def parse_fields(pairs: dict[str, str], path: Path) -> tuple[date, int]:
    try:
        validated = date.fromisoformat(pairs["validated"])
    except ValueError as exc:
        raise ValueError(
            f"{path}: 'validated' is not an ISO date ({pairs['validated']!r})"
        ) from exc
    try:
        horizon_days = int(pairs["review_horizon_days"])
    except ValueError as exc:
        raise ValueError(
            f"{path}: 'review_horizon_days' is not an integer "
            f"({pairs['review_horizon_days']!r})"
        ) from exc
    return validated, horizon_days


def stale_banner(target: Target, validated: date, horizon_days: int) -> str:
    pad = max(0, (65 - len(target.banner_title) - 2) // 2)
    title = f"{'=' * pad} {target.banner_title} {'=' * pad}"
    return (
        f"{title}\n"
        f"{target.rel_path.as_posix()}: assumptions last validated\n"
        f"{validated.isoformat()}, horizon {horizon_days} days exceeded. "
        "This check only knows the date -\n"
        "a human or current-session agent must review:\n"
        f"{target.review_hint}, re-stamp 'validated:'.\n"
        "Exit 1 = review recommended, not an error (cf. sync script).\n"
        f"{'=' * len(title)}"
    )


def validate_structure_tree(text: str, root: Path, path: Path) -> None:
    if "## Project Structure" not in text:
        return
    section = text.split("## Project Structure", 1)[1]
    if section.count("```") < 2:
        return
    stack: list[str] = []
    for line in section.split("```", 2)[1].splitlines():
        marker = max(line.find("├"), line.find("└"))
        if marker < 0:
            continue
        name = line[marker:].split("── ", 1)[-1].split("#", 1)[0].strip().rstrip("/")
        if not name:
            continue
        del stack[marker // 4 :]
        stack.append(name)
        rel = Path(*stack)
        if not (root / rel).exists():
            raise ValueError(
                f"{path}: Project Structure names '{rel.as_posix()}' which does "
                "not exist - update the tree in the same commit that changes "
                "the structure"
            )


def validate_agent_governance(root: Path, path: Path) -> None:
    agents = root / AGENTS_MD_REL_PATH
    claude = root / CLAUDE_MD_REL_PATH
    if not agents.is_file():
        raise ValueError(f"{path}: CLAUDE.md requires AGENTS.md as shared governance")
    agents_text = agents.read_text(encoding="utf-8")
    claude_text = claude.read_text(encoding="utf-8")
    if "@AGENTS.md" not in claude_text:
        raise ValueError(f"{path}: CLAUDE.md must import @AGENTS.md")
    forbidden = ("## Hard Rules", "## Dependencies", "## Must-Know Map")
    repeated = [heading for heading in forbidden if heading in claude_text]
    if repeated:
        raise ValueError(
            f"{path}: shared governance duplicated in CLAUDE.md: {repeated}"
        )
    validate_structure_tree(agents_text, root, agents)


def validate_ontogate_status(pairs: dict[str, str], root: Path, path: Path) -> None:
    status = pairs.get("ontogate", "not-adopted")
    if status == "not-adopted":
        return
    if not (root / status).is_file():
        raise ValueError(
            f"{path}: 'ontogate: {status}' claims adoption but that gate does "
            "not exist - OntoGate is binding once adopted; install the gate or "
            "set 'ontogate: not-adopted'"
        )


def check_target(root: Path, target: Target) -> int:
    path = root / target.rel_path
    if not path.is_file():
        print(f"skill assumptions: {target.label} not present; nothing to validate")
        return 0
    text = path.read_text(encoding="utf-8")
    if target.optional and target.begin not in text:
        print(f"skill assumptions: {target.label} not present; nothing to validate")
        return 0
    try:
        pairs = extract_block(text, target, path)
        validated, horizon_days = parse_fields(pairs, path)
        if target.claude_md_checks:
            validate_agent_governance(root, path)
            validate_ontogate_status(pairs, root, path)
    except ValueError as exc:
        print(f"skill assumptions: {exc}", file=sys.stderr)
        return 2
    due = validated + timedelta(days=horizon_days)
    today = date.today()
    if today > due:
        print(stale_banner(target, validated, horizon_days))
        return 1
    remaining = (due - today).days
    print(
        f"skill assumptions: {target.label} validated {validated.isoformat()}, "
        f"fresh for another {remaining} days"
    )
    return 0


def check(root: Path) -> int:
    return max(check_target(root, target) for target in TARGETS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate dated assumption blocks (food chain, CLAUDE.md)."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="project root containing .claude/ (default: this repo)",
    )
    args = parser.parse_args()
    return check(args.root)


if __name__ == "__main__":
    sys.exit(main())
