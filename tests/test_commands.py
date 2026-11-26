import unittest

from tests import helpers  # noqa: F401
import commands


class RouteTests(unittest.TestCase):
    def test_routes(self):
        cases = {
            "explain this concept": "ai",
            "which is better, tea or coffee": "ai",
            "how do I reduce my stress": "ai",
            "hey what's the capital of France": "ai",
            "give me a summary of photosynthesis": "ai",
            "write an email to my teacher": "ai",
            "tell me a joke": "ai",
            "any new emails?": "email",
            "do I have mail": "email",
            "what homework is due?": "classroom",
            "quizzes?": "classroom",
            "what is due today": "classroom",
            "emails and homework": "briefing",
            "briefing": "briefing",
            "Hi": "briefing",
            "hi jarvis": "briefing",
            "good morning": "briefing",
            "what\u2019s new": "briefing",
            "what do i have": "briefing",
            "quit": "quit",
            "Exit!": "quit",
            "status": "status",
            "help": "help",
            "   ": "empty",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(commands.route(text), expected)

    def test_wants_context(self):
        self.assertTrue(commands.wants_context("what should I do first today?"))
        self.assertTrue(commands.wants_context("anything urgent in my inbox"))
        self.assertFalse(commands.wants_context("tell me a joke"))
        self.assertFalse(commands.wants_context("explain photosynthesis"))

    def test_speakable(self):
        self.assertEqual(commands.speakable("short reply"), "short reply")
        para = "word " * 200
        self.assertEqual(commands.speakable(para), para)  # one paragraph: spoken in full
        lst = "\n".join(f"line {i} " + "x" * 50 for i in range(10))
        out = commands.speakable(lst)
        self.assertTrue(out.endswith("The rest is on screen."))
        self.assertNotIn("line 9", out)


if __name__ == "__main__":
    unittest.main()
