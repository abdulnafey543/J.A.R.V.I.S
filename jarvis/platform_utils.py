"""Small helpers so the rest of Jarvis does not care which OS it runs on.

Supported: Windows and Linux (tested target: Fedora).
"""
import os
import sys
from pathlib import Path

IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")

# The command a user types to start Python in a terminal.
PY_CMD = "python" if IS_WINDOWS else "python3"


def _is_win(windows):
    return IS_WINDOWS if windows is None else windows


def venv_python(root, windows=None):
    """Path of the virtual-environment Python inside project folder `root`."""
    win = _is_win(windows)
    return Path(root) / ".venv" / ("Scripts" if win else "bin") / ("python.exe" if win else "python")


def venv_py_rel(windows=None):
    """The same path as text, relative to the project folder, for messages."""
    return r".venv\Scripts\python.exe" if _is_win(windows) else ".venv/bin/python"


VENV_PY_REL = venv_py_rel()


def diagnose_venv(venv_dir, windows=None):
    """Classify a .venv folder: 'missing', 'ok', 'foreign' or 'broken'.

    'foreign' means it was built on the other OS (a Windows .venv copied to
    Linux or the reverse), so its interpreter can't run here.
    """
    win = _is_win(windows)
    venv_dir = Path(venv_dir)
    if not venv_dir.exists():
        return "missing"
    own = venv_dir / ("Scripts" if win else "bin") / ("python.exe" if win else "python")
    other = venv_dir / ("bin" if win else "Scripts") / ("python" if win else "python.exe")
    if own.exists():
        return "ok"
    if other.exists():
        return "foreign"
    return "broken"


def make_console_utf8():
    """Make printing safe on every terminal (Windows consoles, piped output)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def ollama_install_hint():
    if IS_WINDOWS:
        return "winget install -e --id Ollama.Ollama   (or download from https://ollama.com/download)"
    return "curl -fsSL https://ollama.com/install.sh | sh"
