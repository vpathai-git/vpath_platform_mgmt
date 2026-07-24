#!/usr/bin/env python3
"""
Project initialization script.

This script helps set up a new project by:
- Creating necessary directories
- Setting up configuration files
- Initializing git repository
- Creating initial commit

Usage:
    python scripts/init_project.py
"""

import json
import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: str, check: bool = True) -> "subprocess.CompletedProcess[str]":
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def create_directories() -> None:
    """Create project directories if they don't exist."""
    directories = [
        "src",
        "tests",
        "docs",
        "data",
        "logs",
        "config",
        "scripts",
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created {directory}/")


def setup_git() -> None:
    """Initialize git and activate the committed pre-commit gate."""
    if not Path(".git").exists():
        run_command("git init")
        print("✓ Initialized git repository")
    else:
        print("✓ Git repository already initialized")
    run_command("git config core.hooksPath githooks")
    print("✓ Pre-commit hook activated (runs 'make check'; bypass: --no-verify)")


def verify_scan_toolchain() -> None:
    """Verify the mandatory CVE-gate toolchain (loud fail with instructions)."""
    result = run_command(
        f"{sys.executable} scripts/scan_dependencies.py --verify-only",
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
        print("✗ trivy missing — the CVE gate is mandatory. Install it, then re-run.")
        sys.exit(result.returncode)
    print("✓ CVE-gate toolchain present (trivy)")


def create_virtual_environment() -> None:
    """Create Python virtual environment."""
    if not Path("venv").exists():
        run_command(f"{sys.executable} -m venv venv")
        print("✓ Created virtual environment")
        print("\nActivate it with:")
        if os.name == "nt":
            print("  venv\\Scripts\\activate")
        else:
            print("  source venv/bin/activate")
    else:
        print("✓ Virtual environment already exists")


def optional_setup_context_statusline() -> None:
    """Offer context visibility (status line + agent hook); writes GLOBAL ~/.claude.

    Opt-in by design: installs two scripts under ~/.claude and wires a statusLine
    plus a UserPromptSubmit hook into ~/.claude/settings.json, affecting EVERY
    project. Two pieces, one feature — the status line shows the user the real
    context fill, and the context-report hook injects the SAME figure into the
    agent's own context (the status line writes a per-session state file the hook
    reads: one source, two consumers). Default is skip; nothing global is written
    without explicit consent. Fails hard if a bundled asset is missing.
    """
    assets = Path(__file__).parent / "assets"
    sl_asset = assets / "statusline-context.sh"
    hook_asset = assets / "context-report.sh"
    for asset in (sl_asset, hook_asset):
        if not asset.exists():
            raise FileNotFoundError(
                f"Bundled context-visibility asset missing: {asset}"
            )

    answer = (
        input(
            "\n📊 Install context visibility (status line + agent hook)? It "
            "writes to your GLOBAL ~/.claude/settings.json, affecting all "
            "projects. (y/N): "
        )
        .strip()
        .lower()
    )
    if answer not in ("y", "yes"):
        print("⊘ Skipped — see context/RECOMMENDED_WAYS_OF_WORKING.md to add it later.")
        return

    claude_dir = Path.home() / ".claude"
    settings = claude_dir / "settings.json"
    sl_target = claude_dir / "statusline-context.sh"
    hook_target = claude_dir / "context-report.sh"
    sl_desired = {
        "type": "command",
        "command": "bash ~/.claude/statusline-context.sh",
        "padding": 0,
    }
    hook_cmd = "bash ~/.claude/context-report.sh"

    data: dict = {}
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))

    existing_sl = data.get("statusLine")
    if existing_sl and existing_sl != sl_desired:
        print(f"  An existing statusLine is configured: {existing_sl}")
        if input("  Overwrite it? (y/N): ").strip().lower() not in ("y", "yes"):
            print("⊘ Kept your existing statusLine; nothing changed.")
            return

    ups = data.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    hooked = any(h.get("command") == hook_cmd for e in ups for h in e.get("hooks", []))

    def _current(target: Path, asset: Path) -> bool:
        return target.exists() and target.read_text(
            encoding="utf-8"
        ) == asset.read_text(encoding="utf-8")

    if (
        existing_sl == sl_desired
        and hooked
        and _current(sl_target, sl_asset)
        and _current(hook_target, hook_asset)
    ):
        print("✓ Context visibility already installed and up to date.")
        return

    claude_dir.mkdir(parents=True, exist_ok=True)
    sl_target.write_text(sl_asset.read_text(encoding="utf-8"), encoding="utf-8")
    sl_target.chmod(0o755)
    hook_target.write_text(hook_asset.read_text(encoding="utf-8"), encoding="utf-8")
    hook_target.chmod(0o755)
    data["statusLine"] = sl_desired
    if not hooked:
        ups.append({"hooks": [{"type": "command", "command": hook_cmd}]})
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"✓ Installed status line + context-report hook; wired both in {settings}.")
    print(
        "  Restart Claude Code (or run /hooks to reload). Undo: delete the two "
        "scripts and remove the 'statusLine' key and the UserPromptSubmit entry."
    )


def completion_chime_supported() -> bool:
    """Return whether this machine can play the bundled completion chime."""
    return sys.platform == "darwin" and Path("/usr/bin/afplay").exists()


def optional_setup_completion_chime() -> None:
    """Offer a Claude Stop-hook completion chime; writes GLOBAL ~/.claude."""
    asset = Path(__file__).parent / "assets" / "completion-chime.sh"
    if not asset.exists():
        raise FileNotFoundError(f"Bundled completion-chime asset missing: {asset}")

    answer = (
        input(
            "\n🔔 Install completion chime? It writes a Stop hook to your "
            "GLOBAL ~/.claude/settings.json, affecting all projects. (y/N): "
        )
        .strip()
        .lower()
    )
    if answer not in ("y", "yes"):
        print("⊘ Skipped completion chime.")
        return
    if not completion_chime_supported():
        raise RuntimeError("completion chime requires macOS with /usr/bin/afplay")

    claude_dir = Path.home() / ".claude"
    settings = claude_dir / "settings.json"
    target = claude_dir / "completion-chime.sh"
    command = "bash ~/.claude/completion-chime.sh"
    data: dict = {}
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))
    stop_hooks = data.setdefault("hooks", {}).setdefault("Stop", [])
    hooked = any(
        h.get("command") == command for e in stop_hooks for h in e.get("hooks", [])
    )
    current = target.exists() and target.read_text(encoding="utf-8") == asset.read_text(
        encoding="utf-8"
    )
    if hooked and current:
        print("✓ Completion chime already installed and up to date.")
        return

    claude_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(asset.read_text(encoding="utf-8"), encoding="utf-8")
    target.chmod(0o755)
    if not hooked:
        stop_hooks.append({"hooks": [{"type": "command", "command": command}]})
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"✓ Installed completion chime Stop hook in {settings}.")


def main() -> None:
    """Main initialization function."""
    print("🚀 Initializing project...\n")

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    create_directories()
    setup_git()
    verify_scan_toolchain()
    create_virtual_environment()
    optional_setup_context_statusline()
    optional_setup_completion_chime()

    print("\n✅ Project initialization complete!\n\nNext steps:")
    print("1. Activate virtual environment")
    print("2. Run: pip install -r requirements.txt")
    print("3. Run: pip install -e .")
    print("4. Try: python -m vpath_hello_world")


if __name__ == "__main__":
    main()
