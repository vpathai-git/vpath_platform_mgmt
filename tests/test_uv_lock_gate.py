from pathlib import Path


def test_uv_lock_check_is_first_gate_step() -> None:
    makefile = Path(__file__).resolve().parents[1] / "Makefile"
    lines = makefile.read_text(encoding="utf-8").splitlines()
    check_line = lines.index("check:")
    first_step = next(line.strip() for line in lines[check_line + 1 :] if line)
    assert first_step == "uv lock --check"
