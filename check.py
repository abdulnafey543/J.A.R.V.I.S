import shutil

import auth
import brain
import platform_utils
import voice


def check(name, ok, hint=""):
    print("  [%s] %s %s" % ("OK" if ok else "MISSING", name, hint if hint and not ok else ""))
    return ok


def main():
    print("Jarvis pre-flight check")

    print("\n1) Google")
    check("client_secret.json", auth.CLIENT_SECRET.exists(),
          "-> see docs/GOOGLE_SETUP.md, put the file in: " + str(auth.CRED_DIR))
    ok, msg = auth.check_credentials()
    check("Logged in with a valid token", ok,
          "-> " + msg.replace("\n", " "))

    print("\n2) Local AI (Ollama)")
    online = brain.is_ollama_online()
    check("Ollama server running", online,
          "-> install: " + platform_utils.ollama_install_hint() + "   then start the Ollama app or run: ollama serve")
    if online:
        models = brain.list_models()
        chosen = brain.suggest_model()
        check(f"AI model installed ({chosen})", brain.model_available(chosen, models),
              f"-> run:  ollama pull {chosen}")
        if models:
            print("     Models found: " + ", ".join(models[:6]))

    print("\n3) Voice")
    ok, name, err = voice.probe_tts()
    check("Text-to-speech" + (f" ({name})" if ok else ""), ok, f"-> {err}. {voice._fix_hint()}")
    try:
        import sounddevice as sd
        check("Mic library (sounddevice)", True)
        try:
            sd.query_devices(kind="input")
            check("Microphone detected", True)
        except Exception as e:  # noqa: BLE001
            check("Microphone detected", False, f"-> {e}. {voice._MIC_HELP}")
    except ImportError:
        check("Mic library (sounddevice)", False, "-> run:  " + platform_utils.PY_CMD + " setup.py")
    except OSError:
        check("Mic library (PortAudio)", False, "-> Fedora: sudo dnf install portaudio")
    if shutil.which("pactl") or shutil.which("pacmd"):
        print("     Tip: make sure your mic is not muted in your sound settings.")
    print("     Note: voice *input* uses Google's online speech service; typing stays fully local.")

    print("\nIf everything shows OK, run:  " + platform_utils.PY_CMD + " run.py   (add --voice to talk)")


if __name__ == "__main__":
    main()
