"""Standalone-spawn entrypoint.

The platform's standalone supervisor (spawnPythonMcp) runs `python server.py`
with PORT injected. We delegate to the VpathService app in src/main.py served by
uvicorn. (On the cluster the Dockerfile runs `uvicorn main:app` directly; this
shim only exists to satisfy the standalone supervisor's server.py contract.)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import uvicorn  # noqa: E402
from main import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8020")))
