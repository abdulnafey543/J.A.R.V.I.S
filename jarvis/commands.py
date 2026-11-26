"""Decide what a typed or spoken line means. Pure functions, no I/O.

Matching is on whole words, so "explain this" is never mistaken for the
greeting "hi" and "reduce" is never mistaken for "due".
"""
import re

QUIT_WORDS = {"quit", "exit", "bye", "goodbye"}
HELP_PHRASES = {"help", "what can you do", "help me"}
EMAIL_TERMS = ("email", "emails", "mail", "inbox")
CLASS_TERMS = (
    "classroom", "homework", "hw", "assignment", "assignments",
    "quiz", "quizzes", "due", "overdue", "coursework",
)
# Whole-utterance greetings / briefing requests.
GREETINGS = {
    "hi", "hello", "hey", "hi jarvis", "hello jarvis", "hey jarvis",
    "morning", "good morning", "summary", "overview", "briefing",
}
BRIEF_TERMS = ("briefing", "brief me", "overview", "what do i have", "what's new", "whats new")
# If the user asks for any of these they want the AI, not a data dump.
AI_VETO = (
    "write", "draft", "compose", "explain", "translate", "define",
    "meaning", "difference", "how to", "how do",
)
# Questions mentioning these benefit from the user's Google data as context.
CONTEXT_TERMS = (
    "email", "emails", "mail", "inbox", "unread", "homework", "assignment",
    "assignments", "quiz", "quizzes", "due", "class", "classes", "classroom",
    "schedule", "today", "tomorrow", "week", "urgent", "priority",
    "priorities", "deadline", "deadlines", "overdue", "plan", "busy", "study",
)


def _norm(text):
    text = (text or "").lower().replace("\u2019", "'")
    return " ".join(re.findall(r"[a-z0-9']+", text))


def _has(norm, terms):
    padded = f" {norm} "
    return any(f" {t} " in padded for t in terms)


def route(text):
    """Return one of: empty, quit, status, help, email, classroom, briefing, ai."""
    n = _norm(text)
    if not n:
        return "empty"
    if n in QUIT_WORDS:
        return "quit"
    if n == "status":
        return "status"
    if n in HELP_PHRASES:
        return "help"
    if _has(n, AI_VETO):
        return "ai"
    has_email = _has(n, EMAIL_TERMS)
    has_class = _has(n, CLASS_TERMS)
    if has_email and has_class:
        return "briefing"
    if has_email:
        return "email"
    if has_class:
        return "classroom"
    greeting = " ".join(re.sub(r"\b(jarvis|please)\b", "", n).split())
    if greeting in GREETINGS or (len(n.split()) <= 6 and _has(n, BRIEF_TERMS)):
        return "briefing"
    return "ai"


def wants_context(text):
    """Should the AI be given the user's emails/assignments for this question?"""
    return _has(_norm(text), CONTEXT_TERMS)


def speakable(reply, max_chars=240, max_lines=3):
    """Short version of a long multi-line reply for text-to-speech.

    Long lists are read in part; the full text is always printed on screen.
    Single paragraphs (normal AI answers) are spoken in full.
    """
    lines = [ln.strip() for ln in reply.splitlines() if ln.strip()]
    if len(lines) <= max_lines:
        return reply
    spoken = " ".join(lines[:max_lines])
    if len(spoken) > max_chars:
        spoken = spoken[:max_chars].rsplit(" ", 1)[0]
    return spoken + " ... The rest is on screen."
