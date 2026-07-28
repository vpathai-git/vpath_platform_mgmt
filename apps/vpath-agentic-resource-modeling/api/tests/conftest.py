"""Make the app's ``src/`` importable when the suite runs against a source tree
(the api-install gate installs the package; a local ``pytest`` run does not)."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
