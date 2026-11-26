#!/usr/bin/env python3
"""Jarvis setup: the one recommended installer (Windows, Fedora, other Linux).

    python setup.py       (Windows)
    python3 setup.py      (Linux)

Options:  --yes        answer "yes" to every question
          --no-ollama  skip the Ollama / AI model steps
"""
import argparse
import ctypes.util
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import platform_utils as pu  # noqa: E402
import brain  # noqa: E402  (standard library only, safe before the venv exists)

IS_WINDOWS, IS_LINUX = pu.IS_WINDOWS, pu.IS_LINUX
VENV = ROOT / ".venv"
VENV_PY = pu.venv_python(ROOT)
MODEL = brain.DEFAULT_MODEL
MIN_PY = (3, 9)
ASSUME_YES = False
problems = []  # non-fatal issues, listed again at the end

# (tool, install command, {need: package name})
PKG_TABLE = [
    ("dnf", ["sudo", "dnf", "install", "-y"], {"espeak": "espeak-ng", "portaudio": "portaudio"}),
    ("apt-get", ["sudo", "apt-get", "install", "-y"], {"espeak": "espeak-ng", "portaudio": "libportaudio2"}),
    ("pacman", ["sudo", "pacman", "-S", "--noconfirm"], {"espeak": "espeak-ng", "portaudio": "portaudio"}),
]


class SetupError(Exception):
    """A fatal problem; the message tells the user what to do."""


def run(cmd, **kwargs):
    """Run a command from the project folder; never raises on failure."""
    try:
        return subprocess.run([str(c) for c in cmd], cwd=ROOT, **kwargs)
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def ask(question):
    if ASSUME_YES:
        return True
    try:
        return input(f"  {question} [y/N] ").strip().lower() == "y"
    except EOFError:
        return False


def has_portaudio():
    if ctypes.util.find_library("portaudio"):
        return True
    ldconfig = shutil.which("ldconfig") or "/sbin/ldconfig"
    try:
        out = subprocess.run([ldconfig, "-p"], capture_output=True, text=True).stdout
    except OSError:
        return False
    return "libportaudio.so.2" in out


def has_espeak():
    return bool(shutil.which("espeak-ng") or shutil.which("espeak"))


# --- steps -------------------------------------------------------------------

def step_python():
    if sys.version_info < MIN_PY:
        raise SetupError(f"Python {MIN_PY[0]}.{MIN_PY[1]}+ is required (you have {sys.version.split()[0]}).")


def step_venv():
    print("\n[1/4] Creating Python environment...")
    state = pu.diagnose_venv(VENV)
    if state == "ok" and run([VENV_PY, "-c", "import sys"], capture_output=True).returncode != 0:
        state = "broken"
    if state in ("foreign", "broken"):
        why = ("was created on a different operating system"
               if state == "foreign" else "is broken (its Python is gone, e.g. after an upgrade)")
        print(f"  The existing .venv folder {why} and can't be used here.")
        print("  It is safe to delete: Jarvis rebuilds it. Your credentials/ folder is not touched.")
        if not ask("Delete .venv and rebuild it now?"):
            raise SetupError(f"Delete the .venv folder yourself, then run  {pu.PY_CMD} setup.py  again.")
        shutil.rmtree(VENV)
        state = "missing"
    if state == "missing":
        r = run([sys.executable, "-m", "venv", VENV])
        if r.returncode != 0 or not VENV_PY.exists():
            hint = " On Debian/Ubuntu:  sudo apt install python3-venv." if IS_LINUX else ""
            raise SetupError("Couldn't create the virtual environment." + hint)

    print("[2/4] Installing Python packages...")
    run([VENV_PY, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    if run([VENV_PY, "-m", "pip", "install", "-r", "requirements.txt"]).returncode != 0:
        raise SetupError("Installing Python packages failed. Check your internet connection, "
                         "read the error above, then run setup again.")


def step_voice():
    print("[3/4] Checking voice engine and microphone support...")
    if IS_LINUX:
        missing = [n for n, ok in (("espeak", has_espeak()), ("portaudio", has_portaudio())) if not ok]
        if missing:
            manager = next((row for row in PKG_TABLE if shutil.which(row[0])), None)
            if manager is None:
                problems.append("Install espeak-ng and PortAudio with your package manager "
                                "(Fedora: sudo dnf install espeak-ng portaudio).")
            else:
                tool, cmd, names = manager
                pkgs = [names[m] for m in missing]
                print(f"  Installing {', '.join(pkgs)} with {tool} (needs your password)...")
                if run(cmd + pkgs).returncode != 0:
                    problems.append(f"Couldn't install {', '.join(pkgs)} ({tool} failed). Install them "
                                    f"manually, then run:  {pu.PY_CMD} run.py --check")
                elif not (has_espeak() and has_portaudio()):
                    problems.append("Voice packages were installed but still aren't detected; "
                                    "run:  " + pu.PY_CMD + " run.py --check")
    r = run([VENV_PY, "-c", "import pyttsx3, sounddevice, numpy, speech_recognition"],
            capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()[-1:] or ["unknown error"]
        problems.append("Voice packages failed to load: " + tail[0] + "  (text mode still works)")
    else:
        print("  Voice packages OK.")


def _wait_online(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if brain.is_ollama_online():
            return True
        time.sleep(1)
    return False


def _start_ollama(exe):
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WINDOWS:
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 8) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 512)
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen([exe, "serve"], **kwargs)
    except OSError as e:
        return False, str(e)
    return _wait_online(20), ""


def _find_ollama():
    exe = shutil.which("ollama")
    if exe or not IS_WINDOWS:
        return exe
    import os
    guess = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(guess) if guess.exists() else None


def step_ollama():
    print("[4/4] Checking Ollama (local AI)...")
    exe = _find_ollama()
    if not exe:
        if IS_WINDOWS and shutil.which("winget") and ask("Ollama not found. Install it with winget?"):
            run(["winget", "install", "-e", "--id", "Ollama.Ollama"])
        elif IS_LINUX and ask("Ollama not found. Install it now (downloads and runs the official script)?"):
            subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True)
        exe = _find_ollama()
    if not exe:
        problems.append("Ollama isn't installed. Install it:  " + pu.ollama_install_hint())
        return
    if not brain.is_ollama_online():
        print("  Starting the Ollama server...")
        ok, err = _start_ollama(exe)
        if not ok:
            problems.append("Ollama is installed but its server didn't start"
                            + (f" ({err})" if err else "") + ". Open the Ollama app or run:  ollama serve")
            return
    if brain.model_available(MODEL):
        print(f"  Model {MODEL} is ready.")
        return
    if ask(f"Download the AI model {MODEL} (~2 GB)?"):
        run([exe, "pull", MODEL])
    if not brain.model_available(MODEL):
        problems.append(f"The AI model {MODEL} isn't installed. Run:  ollama pull {MODEL}")


def print_summary():
    if problems:
        print(f"\nSetup finished with {len(problems)} thing(s) to fix:")
        for p in problems:
            print("  - " + p)
    else:
        print("\nSetup finished with no problems.")
    print("\n=========================================")
    print("  Next: Google account setup")
    print("=========================================")
    print("1) Follow docs/GOOGLE_SETUP.md and put client_secret.json in the 'credentials' folder")
    print(f"2) Log in:            {pu.VENV_PY_REL} setup_google.py")
    print(f"3) Check everything:  {pu.PY_CMD} run.py --check")
    print(f"4) Start Jarvis:      {pu.PY_CMD} run.py          (voice: add --voice)\n")


def main(argv=None):
    global ASSUME_YES
    parser = argparse.ArgumentParser(description="Set up Jarvis.")
    parser.add_argument("--yes", action="store_true", help="answer yes to all questions")
    parser.add_argument("--no-ollama", action="store_true", help="skip Ollama steps")
    args = parser.parse_args(argv)
    ASSUME_YES = args.yes
    print("=========================================")
    print("  Jarvis setup")
    print("=========================================")
    try:
        step_python()
        step_venv()
        step_voice()
        if args.no_ollama:
            print("[4/4] Skipping Ollama.")
        else:
            step_ollama()
    except SetupError as e:
        print(f"\nSetup stopped: {e}")
        sys.exit(1)
    print_summary()


if __name__ == "__main__":
    main()
