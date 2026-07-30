"""Tests for scripts/check_no_logged_credentials.py -- gate plus red drill.

Two halves, and both are needed for the gate to mean anything:

**The gate.** :func:`test_repository_is_clean` runs the checker over this
repository and demands exit 0.  That is the standing assertion.

**The red drill.** A gate nobody has seen fail is a decoration.  Every rule here
is shown going red on a synthetic violation before the repository is shown
green, so "green" is evidence rather than a hope.  The drill also covers the
failure mode that matters most: the checker must exit *undetermined* -- never 0
-- when it cannot establish the facts.

Every credential-shaped string in this file is invented for the drill.  No value
from any real system appears here, and none may ever be added.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_no_logged_credentials as gate  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

# Invented for this drill.  Deliberately not placeholder-shaped, so the checker
# treats it as a value -- that is the whole point of a red drill.
FAKE_VALUE = "rd0000notarealsecret"


@pytest.fixture(autouse=True)
def _hermetic_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """When this suite runs inside a git hook (the pre-commit gate during a
    pathspec commit), git exports GIT_INDEX_FILE/GIT_DIR; inherited by the
    fixture's git subprocesses they redirect `git add` into the PARENT
    repository's commit index (observed: the drill's broken.py staged into a
    real commit, blob 3ef997aa unreachable, commit failed on tree build).
    Scrub every GIT_* variable so fixture repos and checker runs are hermetic."""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)


def make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """A throwaway git repository -- the checker only looks at tracked files."""
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def run_gate(root: Path) -> int:
    return gate.main(["--root", str(root), "--exclude", "___none___"])


# --- the gate -------------------------------------------------------------


def test_repository_is_clean() -> None:
    """No credential value reaches an output or a tracked file in this repo."""
    assert gate.main(["--root", str(REPO_ROOT)]) == gate.EXIT_OK


# --- red drill: every rule is shown failing -------------------------------


def test_red_drill_source_rule_fails_on_printed_credential(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {"leak.py": "password = get()\nprint(f'the password is {password}')\n"},
    )
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("SOURCE", 2)]
    assert run_gate(root) == gate.EXIT_VIOLATION


def test_red_drill_source_rule_fails_on_logging_call(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {"leak.py": "import logging\nlogging.info('token=%s', api_token)\n"},
    )
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("SOURCE", 2)]


def test_red_drill_literal_rule_fails_on_hardcoded_python(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"conf.py": f'ADMIN_PASSWORD = "{FAKE_VALUE}"\n'})
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("LITERAL", 1)]


def test_red_drill_literal_rule_fails_on_hardcoded_shell(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"setup.sh": f"DEFAULT_PASSWORD={FAKE_VALUE}\n"})
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("LITERAL", 1)]


def test_red_drill_pipeline_rule_fails_on_unredacted_log(tmp_path: Path) -> None:
    """Both shapes the install pipeline emits, caught in a captured log."""
    root = make_repo(
        tmp_path,
        {
            "run.log": (
                f"* Password: {FAKE_VALUE}   *\n"
                f"[info] someuser / {FAKE_VALUE} (some-role)\n"
            )
        },
    )
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("PIPELINE", 1), ("PIPELINE", 2)]


def test_violation_output_never_repeats_the_value(tmp_path: Path) -> None:
    """The finding names the place.  Repeating the value would re-leak it."""
    root = make_repo(tmp_path, {"run.log": f"* Password: {FAKE_VALUE}   *\n"})
    rendered = "\n".join(
        v.render(root) for v in gate.scan(root, gate.tracked_files(root), [])
    )
    assert FAKE_VALUE not in rendered
    assert "run.log:1" in rendered


# --- the drill's other half: green must be reachable and honest -----------


def test_redacted_log_line_passes(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"run.log": "* Password: <redacted-credential>   *\n"})
    assert gate.scan(root, gate.tracked_files(root), []) == []


def test_placeholders_and_env_references_pass(tmp_path: Path) -> None:
    root = make_repo(
        tmp_path,
        {
            "ok.sh": 'ADMIN_PASSWORD="$KEYCLOAK_ADMIN_PASSWORD"\nTOKEN=<value>\n',
            "ok.py": 'API_KEY = ""\nSECRET = "changeme"\n',
        },
    )
    assert gate.scan(root, gate.tracked_files(root), []) == []


def test_names_that_point_at_a_secret_are_not_the_secret(tmp_path: Path) -> None:
    """`secretName` and `max_tokens` are metadata, not credentials."""
    root = make_repo(
        tmp_path,
        {
            "deploy.yaml": "secretName: platform-api-secrets\n",
            "call.py": "print(f'used {max_tokens} of {prompt_tokens}')\n",
        },
    )
    assert gate.scan(root, gate.tracked_files(root), []) == []
    assert gate.names_a_credential("secretName") is False
    assert gate.names_a_credential("max_tokens") is False
    assert gate.names_a_credential("KEYCLOAK_ADMIN_PASSWORD") is True
    assert gate.names_a_credential("api_key") is True


# --- red drill: the three blind spots closed on 2026-07-28 ----------------
#
# Each blind spot gets both halves: the violation it used to miss, shown going
# red, and the shape it must NOT fire on, shown staying green.  An exemption
# without a green test is just a new blind spot with better manners.


def test_red_drill_kts_file_is_scanned_at_all(tmp_path: Path) -> None:
    """Blind spot 1: `.kts` was absent from TEXT_SUFFIXES, so 27 tracked gradle
    scripts -- including the one that writes the demo cheat sheet -- were never
    opened.  They carry their real work as shell inside raw strings."""
    assert ".kts" in gate.TEXT_SUFFIXES
    root = make_repo(
        tmp_path,
        {"build.gradle.kts": 'exec("""\n  log::info "pw=$ADMIN_PASSWORD"\n""")\n'},
    )
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("SOURCE", 2)]
    assert run_gate(root) == gate.EXIT_VIOLATION


def test_red_drill_shell_log_call_leaks(tmp_path: Path) -> None:
    """Blind spot 2: SOURCE was Python-only, so this platform's own logging
    vocabulary (`log::info`, lib/log.sh) could carry a value untouched."""
    root = make_repo(
        tmp_path,
        {"start.sh": 'log::info "NEXTAUTH_SECRET=$NEXTAUTH_SECRET"\n'},
    )
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("SOURCE", 1)]


def test_red_drill_echo_weaving_a_value_into_a_message_leaks(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"leak.sh": 'echo "  Password: $PASSWORD"\n'})
    assert [
        (v.rule, v.line) for v in gate.scan(root, gate.tracked_files(root), [])
    ] == [("SOURCE", 1)]


def test_bare_echo_of_a_value_is_a_return_channel_not_a_log(tmp_path: Path) -> None:
    """`echo "$SECRET"` is how a shell function returns a value; every caller in
    this platform captures it.  `printf -v` never reaches a stream at all."""
    root = make_repo(
        tmp_path,
        {
            "return.sh": (
                'echo "$CLIENT_SECRET"\n'
                "printf '%s\\n' \"$CLIENT_SECRET\"\n"
                "printf -v quoted_token '%q' \"$TOKEN\"\n"
            )
        },
    )
    assert gate.scan(root, gate.tracked_files(root), []) == []


def test_command_substitution_is_a_capture_not_an_output(tmp_path: Path) -> None:
    """Both directions: an output call inside `$(...)` hands its text to the
    shell, and an output call containing one prints the subshell's verdict."""
    root = make_repo(
        tmp_path,
        {
            "capture.sh": (
                "ERR=$(printf '%s' \"$TOKEN_RESP\" | jq -r .error)\n"
                'echo "has colon: $([[ "$JIRA_ACCESS_TOKEN" == *:* ]] && echo yes)"\n'
            )
        },
    )
    assert gate.scan(root, gate.tracked_files(root), []) == []


def test_red_drill_password_inside_a_connection_string(tmp_path: Path) -> None:
    """Blind spot 3: a DSN hides a value from every key-based rule, because the
    DSN's own key (`DATABASE_URL`) names a location, not a secret."""
    root = make_repo(
        tmp_path,
        {"app.env": f"DATABASE_URL=postgresql://appuser:{FAKE_VALUE}@db:5432/app\n"},
    )
    violations = gate.scan(root, gate.tracked_files(root), [])
    assert [(v.rule, v.line) for v in violations] == [("URL", 1)]
    assert FAKE_VALUE not in violations[0].render(root)


def test_connection_string_without_a_value_passes(tmp_path: Path) -> None:
    """A reference, a template and a userinfo-less URL are all not values."""
    root = make_repo(
        tmp_path,
        {
            "ok.env": (
                "A_URL=postgresql://appuser:${PGPASSWORD}@db:5432/app\n"
                "B_URL=postgresql://appuser:password@db:5432/app\n"
                "C_URL=postgresql://db:5432/app\n"
            )
        },
    )
    assert gate.scan(root, gate.tracked_files(root), []) == []


def test_a_length_is_not_a_value(tmp_path: Path) -> None:
    """Printing `len(token)` is the honest diagnostic that replaces printing the
    token -- the gate must not punish the fix it asked for."""
    root = make_repo(
        tmp_path,
        {
            "ok.py": 'token = mint()\nprint(f"minted ok ({len(token)} chars)")\n',
            "leak.py": 'token = mint()\nprint(f"token: {token[:30]}...")\n',
        },
    )
    assert [
        (str(v.path.name), v.line)
        for v in gate.scan(root, gate.tracked_files(root), [])
    ] == [("leak.py", 2)]


def test_shell_names_that_point_or_count_are_not_values(tmp_path: Path) -> None:
    """Measured against the server checkout: every one of these was a false
    alarm before REFERENCE_RE learned the shell's vocabulary."""
    for name in (
        "TOKEN_URL",
        "SECRET_SET_COUNT",
        "token_attempt",
        "secretMap",
        "k8s_secret_name",
        "gitea_oidc_secret_name",
    ):
        assert gate.names_a_credential(name) is False, name
    for name in ("NEXTAUTH_SECRET", "KEYCLOAK_ADMIN_PASSWORD", "CLIENT_SECRET"):
        assert gate.names_a_credential(name) is True, name


def test_self_declaring_non_secrets_pass_but_a_bare_prefix_does_not(
    tmp_path: Path,
) -> None:
    """A value may declare that it guards nothing -- but only by saying so.  A
    bare `dev-`/`sandbox-` prefix is NOT a declaration and must still fail."""
    for value in (
        "dev-secret-do-not-use-in-production",
        "sandbox-dev-secret-for-local-testing-only",
        "unused",
        "REFERENCE_TO_K8S_SECRET_keycloak_admin_password",
        "<rotate-me-not-a-live-secret>",
    ):
        assert gate.PLACEHOLDER_RE.match(value), value
    for value in ("dev-" + FAKE_VALUE, "sandbox-" + FAKE_VALUE, FAKE_VALUE):
        assert not gate.PLACEHOLDER_RE.match(value), value
    root = make_repo(tmp_path, {"sandbox.sh": f'export API_KEY="dev-{FAKE_VALUE}"\n'})
    assert [
        (v.rule, v.line) for v in gate.scan(root, gate.tracked_files(root), [])
    ] == [("LITERAL", 1)]


# --- the anti-soft-pass property ------------------------------------------


def test_unestablishable_is_undetermined_never_a_pass(tmp_path: Path) -> None:
    """A directory git does not track must not read as 'no violations'."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    (plain / "leak.sh").write_text(f"PASSWORD={FAKE_VALUE}\n", encoding="utf-8")
    assert gate.main(["--root", str(plain)]) == gate.EXIT_UNDETERMINED


def test_unparsable_python_is_undetermined_never_a_pass(tmp_path: Path) -> None:
    root = make_repo(tmp_path, {"broken.py": "def (\n"})
    with pytest.raises(gate.CheckError):
        gate.scan(root, gate.tracked_files(root), [])
