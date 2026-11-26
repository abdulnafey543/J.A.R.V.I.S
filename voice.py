import queue
import shutil
import subprocess
import sys
import threading

import platform_utils

voice_out_enabled = True
voice_in_enabled = False

SAMPLE_RATE = 16000


class VoiceInputError(Exception):
    """Voice input failed for a real reason (not just silence).

    kind == "mic":     no microphone / permission / missing library
    kind == "service": the online speech service could not be reached
    """

    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


# --- Text-to-speech -------------------------------------------------------
# All speaking happens on ONE background thread that owns the speech engine
# (Windows SAPI5/COM must be created and used on the same thread, and it stops
# sentences talking over each other). say() just queues text.

_speech_queue = queue.Queue()
_worker = None
_worker_lock = threading.Lock()
_pending = 0
_pending_cv = threading.Condition()
_warned = False


def _espeak_exe():
    return shutil.which("espeak-ng") or shutil.which("espeak")


def _fix_hint():
    if platform_utils.IS_WINDOWS:
        return "Check Windows Settings > Time & language > Speech for an installed voice."
    return "Install a voice engine:  sudo dnf install espeak-ng   (then run: python3 run.py --check)"


class _Engine:
    """Speech output with detection, recovery and fallback (pyttsx3 -> espeak)."""

    def __init__(self):
        self.name = None
        self.engine = None
        self.error = None

    def init(self):
        errors = []
        if self._init_pyttsx3(errors) or self._init_espeak(errors):
            self.error = None
            return True
        self.name = None
        self.error = "; ".join(errors)
        return False

    def _init_pyttsx3(self, errors):
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
        except Exception as e:  # noqa: BLE001
            errors.append(f"pyttsx3 failed ({type(e).__name__}: {e})")
            return False
        self.engine, self.name = engine, "pyttsx3"
        return True

    def _init_espeak(self, errors):
        if _espeak_exe():
            self.engine, self.name = None, "espeak"
            return True
        errors.append("espeak-ng is not installed")
        return False

    def _speak_once(self, text):
        if self.name == "pyttsx3":
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            r = subprocess.run(
                [_espeak_exe(), "-s", "160", "-v", "en+m3", text],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip() or f"espeak exited with {r.returncode}")

    def speak(self, text):
        """Speak text. Recover from a crashed engine once, then fall back.

        Returns True if the text was spoken, False if no engine works.
        """
        reinit_tried = False
        while self.name is not None:
            try:
                self._speak_once(text)
                return True
            except Exception as e:  # noqa: BLE001
                self.error = f"{self.name} failed ({type(e).__name__}: {e})"
                if self.name == "pyttsx3":
                    self.engine = None
                    if not reinit_tried:
                        reinit_tried = True
                        if self._init_pyttsx3([]):
                            continue
                    if not self._init_espeak([]):
                        self.name = None
                else:
                    self.name = None
        return False


_engine = _Engine()


def probe_tts():
    """Test speech output without speaking. Returns (ok, backend, error)."""
    eng = _Engine()
    ok = eng.init()
    return ok, eng.name, eng.error


def _warn_once(message):
    global _warned
    if not _warned:
        _warned = True
        print(f"[voice] {message}", file=sys.stderr, flush=True)


def _speech_worker():
    global _pending
    if not _engine.init():
        _warn_once(f"Voice output is unavailable: {_engine.error}. {_fix_hint()} Text replies still work.")
    while True:
        text = _speech_queue.get()
        try:
            if not _engine.speak(text):
                _warn_once(f"Voice output stopped working: {_engine.error}. {_fix_hint()}")
        finally:
            with _pending_cv:
                _pending -= 1
                _pending_cv.notify_all()


def _ensure_worker():
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = threading.Thread(target=_speech_worker, daemon=True)
            _worker.start()


def say(text, spoken=None):
    """Print text; speak `spoken` (default: the same text) if voice is on."""
    global _pending
    print(text, flush=True)
    to_say = text if spoken is None else spoken
    if not voice_out_enabled or not to_say:
        return
    _ensure_worker()
    with _pending_cv:
        _pending += 1
    _speech_queue.put(to_say)


def wait_for_speech(timeout=30):
    """Block until Jarvis has finished speaking (or the timeout passes)."""
    with _pending_cv:
        _pending_cv.wait_for(lambda: _pending == 0, timeout)


# --- Speech recognition ---------------------------------------------------

_MIC_HELP = (
    "Windows: Settings > Privacy & security > Microphone (allow desktop apps). "
    "Linux: check the mic isn't muted and that PipeWire/PulseAudio sees it."
)


def _record(timeout, phrase_limit):
    """Record one phrase. Returns AudioData, or None if nobody spoke."""
    import time

    try:
        import numpy as np
        import sounddevice as sd
        import speech_recognition as sr
    except ImportError as e:
        raise VoiceInputError("mic", f"Voice input packages are missing ({e}). Run: {platform_utils.PY_CMD} setup.py")
    except OSError as e:
        raise VoiceInputError("mic", f"The PortAudio library is missing ({e}). Fedora: sudo dnf install portaudio")

    try:
        sd.query_devices(kind="input")
    except Exception as e:  # noqa: BLE001
        raise VoiceInputError("mic", f"No microphone found ({e}). {_MIC_HELP}")

    blocks = []
    state = {"finished": False, "silence": 0.0, "total": 0.0, "spoke": False}

    def callback(indata, frames, t, status):
        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
        elapsed = frames / SAMPLE_RATE
        state["total"] += elapsed
        blocks.append(indata.copy())
        if rms < 0.008:
            state["silence"] += elapsed
        else:
            state["silence"] = 0.0
            state["spoke"] = True
        if (state["spoke"] and state["silence"] > 1.2) or state["total"] > phrase_limit:
            state["finished"] = True

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback):
            start = time.time()
            while not state["finished"] and time.time() - start < timeout:
                time.sleep(0.05)
    except Exception as e:  # noqa: BLE001
        raise VoiceInputError("mic", f"Couldn't open the microphone ({e}). {_MIC_HELP}")

    if not blocks or not state["spoke"]:
        return None
    return sr.AudioData(np.concatenate(blocks).tobytes(), SAMPLE_RATE, 2)


def listen(timeout=6, phrase_limit=8):
    """Return the recognised text, or None if nothing was understood.

    Raises VoiceInputError for real problems so the caller can tell the user
    *why* (no mic vs. no internet) instead of a vague "I didn't catch that".
    """
    if not voice_in_enabled:
        return None
    wait_for_speech()  # don't record Jarvis's own voice
    try:
        import speech_recognition as sr
    except ImportError:
        raise VoiceInputError("mic", f"SpeechRecognition isn't installed. Run: {platform_utils.PY_CMD} setup.py")
    audio = _record(timeout, phrase_limit)
    if audio is None:
        return None
    try:
        # NOTE: recognize_google uploads the audio to Google's speech service.
        return sr.Recognizer().recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        raise VoiceInputError("service", f"Couldn't reach Google's speech service (needs internet): {e}")
