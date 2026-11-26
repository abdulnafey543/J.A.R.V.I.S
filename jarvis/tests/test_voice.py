import contextlib
import io
import sys
import types
import unittest
from unittest import mock

from tests import helpers  # noqa: F401
import voice


def fake_pyttsx3(init):
    return types.SimpleNamespace(init=init)


class Eng:
    """Fake pyttsx3 engine; `fail_times` runAndWait calls raise first."""

    def __init__(self, fail_times=0):
        self.fail_times, self.spoken = fail_times, []

    def setProperty(self, *a):
        pass

    def say(self, text):
        self.spoken.append(text)

    def runAndWait(self):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("engine died")


def patch_modules(**mods):
    return mock.patch.dict(sys.modules, mods)


class EngineTests(unittest.TestCase):
    def test_init_reports_why_nothing_works(self):
        def boom():
            raise OSError("no speech driver")
        with patch_modules(pyttsx3=fake_pyttsx3(boom)), mock.patch("shutil.which", return_value=None):
            eng = voice._Engine()
            self.assertFalse(eng.init())
        self.assertIn("pyttsx3 failed", eng.error)
        self.assertIn("no speech driver", eng.error)
        self.assertIn("espeak-ng is not installed", eng.error)

    def test_falls_back_to_espeak_at_init(self):
        def boom():
            raise OSError("x")
        with patch_modules(pyttsx3=fake_pyttsx3(boom)), mock.patch("shutil.which", return_value="/usr/bin/espeak-ng"):
            eng = voice._Engine()
            self.assertTrue(eng.init())
        self.assertEqual(eng.name, "espeak")

    def test_recovers_from_crashed_engine(self):
        engines = [Eng(fail_times=1), Eng()]
        with patch_modules(pyttsx3=fake_pyttsx3(lambda: engines.pop(0))):
            eng = voice._Engine()
            self.assertTrue(eng.init())
            self.assertTrue(eng.speak("hello"))
        self.assertEqual(eng.name, "pyttsx3")

    def test_falls_back_to_espeak_when_engine_keeps_failing(self):
        ok = types.SimpleNamespace(returncode=0, stderr="")
        with patch_modules(pyttsx3=fake_pyttsx3(lambda: Eng(fail_times=99))), \
                mock.patch("shutil.which", return_value="/usr/bin/espeak-ng"), \
                mock.patch("subprocess.run", return_value=ok) as run:
            eng = voice._Engine()
            eng.init()
            self.assertTrue(eng.speak("hello"))
        self.assertEqual(eng.name, "espeak")
        self.assertEqual(run.call_args[0][0][-1], "hello")

    def test_reports_failure_when_everything_fails(self):
        bad = types.SimpleNamespace(returncode=1, stderr="no audio device")
        with patch_modules(pyttsx3=fake_pyttsx3(lambda: Eng(fail_times=99))), \
                mock.patch("shutil.which", return_value="/usr/bin/espeak-ng"), \
                mock.patch("subprocess.run", return_value=bad):
            eng = voice._Engine()
            eng.init()
            self.assertFalse(eng.speak("hello"))
        self.assertIsNone(eng.name)
        self.assertIn("no audio device", eng.error)

    def test_probe_tts(self):
        with patch_modules(pyttsx3=fake_pyttsx3(lambda: Eng())):
            self.assertEqual(voice.probe_tts(), (True, "pyttsx3", None))


class SayTests(unittest.TestCase):
    def test_say_always_prints_even_when_voice_off(self):
        buf = io.StringIO()
        with mock.patch.object(voice, "voice_out_enabled", False), contextlib.redirect_stdout(buf):
            voice.say("hello there")
        self.assertEqual(buf.getvalue().strip(), "hello there")

    def test_warn_once(self):
        err = io.StringIO()
        with mock.patch.object(voice, "_warned", False), contextlib.redirect_stderr(err):
            voice._warn_once("first")
            voice._warn_once("second")
        self.assertIn("first", err.getvalue())
        self.assertNotIn("second", err.getvalue())


class FakeSR:
    class UnknownValueError(Exception):
        pass

    class RequestError(Exception):
        pass

    def __init__(self, behaviour):
        self.behaviour = behaviour
        outer = self

        class Recognizer:
            def recognize_google(self, audio):
                return outer.behaviour(audio)
        self.Recognizer = Recognizer


class ListenTests(unittest.TestCase):
    def run_listen(self, record, behaviour=lambda a: "text"):
        sr = FakeSR(behaviour)
        with patch_modules(speech_recognition=sr), \
                mock.patch.object(voice, "voice_in_enabled", True), \
                mock.patch.object(voice, "_record", record):
            return voice.listen(), sr

    def test_text_returned(self):
        result, _ = self.run_listen(lambda t, p: object(), lambda a: "hello jarvis")
        self.assertEqual(result, "hello jarvis")

    def test_silence_is_none_not_error(self):
        self.assertIsNone(self.run_listen(lambda t, p: None)[0])

    def test_unrecognised_speech_is_none(self):
        def unknown(audio):
            raise FakeSR.UnknownValueError()
        sr = FakeSR(unknown)
        with patch_modules(speech_recognition=sr), mock.patch.object(voice, "voice_in_enabled", True), \
                mock.patch.object(voice, "_record", lambda t, p: object()):
            self.assertIsNone(voice.listen())

    def test_mic_problem_is_distinguishable(self):
        def no_mic(t, p):
            raise voice.VoiceInputError("mic", "No microphone found")
        with patch_modules(speech_recognition=FakeSR(None)), mock.patch.object(voice, "voice_in_enabled", True), \
                mock.patch.object(voice, "_record", no_mic):
            with self.assertRaises(voice.VoiceInputError) as cm:
                voice.listen()
        self.assertEqual(cm.exception.kind, "mic")

    def test_network_problem_is_distinguishable(self):
        def offline(audio):
            raise FakeSR.RequestError("no internet")
        sr = FakeSR(offline)
        with patch_modules(speech_recognition=sr), mock.patch.object(voice, "voice_in_enabled", True), \
                mock.patch.object(voice, "_record", lambda t, p: object()):
            with self.assertRaises(voice.VoiceInputError) as cm:
                voice.listen()
        self.assertEqual(cm.exception.kind, "service")

    def test_disabled_returns_none(self):
        with mock.patch.object(voice, "voice_in_enabled", False):
            self.assertIsNone(voice.listen())


if __name__ == "__main__":
    unittest.main()
