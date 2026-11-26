#!/usr/bin/env python3
"""Start Jarvis - works on Windows and Linux.

    python run.py [--voice | --check | --setup]      (Windows)
    python3 run.py [--voice | --check | --setup]     (Linux)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from platform_utils import PY_CMD, diagnose_venv, venv_python  # noqa: E402

VENV_PY = venv_python(ROOT)

if diagnose_venv(ROOT / ".venv") != "ok":
    print(f"Not installed yet (or .venv was made on another OS). Run:  {PY_CMD} setup.py")
    sys.exit(1)

args = sys.argv[1:]
script = "main.py"
if args and args[0] == "--check":
    script, args = "check.py", args[1:]

try:
    sys.exit(subprocess.call([str(VENV_PY), str(ROOT / script), *args], cwd=ROOT))
except KeyboardInterrupt:
    sys.exit(0)
