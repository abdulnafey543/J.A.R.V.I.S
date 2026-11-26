import datetime
import os
import sys
import time
import traceback

import auth
import brain
import classroom
import commands
import gmail
import platform_utils
import voice

ASCII_LOGO = r"""
   ╔═══╗ ═╚═╗
   ╠═══╣╔═══╗
   ╚═══╝╚═══╝
"""

HELP_TEXT = """Jarvis understands things like:
  "any new emails?"          -> shows unread emails
  "what homework is due?"    -> shows pending Classroom work
  "quizzes?"                 -> shows pending quizzes
  "briefing" / "hello"       -> emails + homework at a glance
  "quit" / "exit"            -> leave

Anything else goes to your local AI (Ollama), which remembers the last few
messages and can see your emails/homework when your question is about them.
Type "status" to check the setup."""

CACHE_TTL = 600   # seconds: Google data the AI may reuse
FRESH_TTL = 60    # seconds: data shown for an explicit email/homework request

_cache = {}
_model = brain.DEFAULT_MODEL
_conversation = brain.Conversation()


# --- Google data (cached, fetched only when needed) -------------------------

def friendly_error(e):
    if isinstance(e, auth.AuthError):
        return str(e)
    if isinstance(e, ImportError):
        return f"A required package is missing ({e}). Run:  {platform_utils.PY_CMD} setup.py"
    status = getattr(getattr(e, "resp", None), "status", None)
    if status == 403:
        return (f"{type(e).__name__}: {e} (is the Gmail / Classroom API enabled in "
                "your Google Cloud project? See docs/GOOGLE_SETUP.md)")
    return f"{type(e).__name__}: {e}"


def _fetch(key, loader, max_age):
    """Return (data, error). Successful results are cached for max_age seconds."""
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < max_age:
        return hit[1], None
    try:
        data = loader()
    except Exception as e:  # noqa: BLE001
        return None, friendly_error(e)
    _cache[key] = (time.monotonic(), data)
    return data, None


def get_emails(max_age=FRESH_TTL):
    return _fetch("emails", gmail.fetch_unread_emails, max_age)


def get_work(max_age=FRESH_TTL):
    return _fetch("work", classroom.fetch_pending_work, max_age)


# --- Formatting (pure, tested) ---------------------------------------------

def work_lines(work, now):
    out = []
    for w in work:
        kind = "QUIZ" if classroom.is_quiz(w) else "ASSIGNMENT"
        state = "" if w["state"] in ("NEW", "CREATED") else f" [{w['state']}]"
        due = w["due"]
        if due is None:
            due_txt = "no date"
        elif due.date() == now.date():
            due_txt = f"today {due:%H:%M}"
        else:
            due_txt = due.strftime("%b %d, %H:%M")
        graded = f", grade: {w['graded']}" if w.get("graded") is not None else ""
        out.append(f"  [{kind}] {w['title']} — {w['course']} (due {due_txt}){state}{graded}")
    return out


def format_work(work, now):
    if not work:
        return "No pending assignments or quizzes. You're all clear!"
    groups = classroom.bucket(work, now)
    lines = []
    for key, label in (("overdue", "OVERDUE"), ("today", "DUE TODAY"),
                       ("upcoming", "UPCOMING"), ("nodue", "NO DUE DATE")):
        if groups[key]:
            lines.append(f"{label} ({len(groups[key])}):")
            lines.extend(work_lines(groups[key], now))
    return "\n".join(lines)


def format_emails(emails, has_more):
    if not emails:
        return "No unread emails."
    count = f"{len(emails)}+" if has_more else str(len(emails))
    lines = [f"UNREAD EMAILS ({count}):"]
    for i, e in enumerate(emails, 1):
        lines.append(f"  {i}. {e['subject']} — from {e['from']}")
    if has_more:
        lines.append("  ...and more in your inbox.")
    return "\n".join(lines)


def build_context(emails, work, now, limit=25):
    """Compact account summary for the AI. Every email/assignment string is
    sanitised because other people wrote it."""
    s = brain.sanitize_untrusted
    lines = [f"Current time: {now:%A %Y-%m-%d %H:%M}"]
    for w in (work or [])[:limit]:
        kind = "quiz" if classroom.is_quiz(w) else "assignment"
        due = f"{w['due']:%Y-%m-%d %H:%M}" if w["due"] else "no due date"
        lines.append(f"- {kind}: {s(w['title'])} | course: {s(w['course'])} | due: {due}")
    for e in (emails or [])[:limit]:
        lines.append(f"- email: {s(e['subject'])} | from: {s(e['from'])}")
    return "\n".join(lines)


# --- Replies -----------------------------------------------------------------

def _warning_lines(warnings):
    return ["Note: " + w for w in warnings[:3]]


def format_briefing():
    edata, eerr = get_emails()
    wdata, werr = get_work()
    if eerr and werr:
        return "I couldn't reach Google: " + eerr
    now = datetime.datetime.now()
    parts = []
    if werr:
        parts.append("Couldn't fetch Classroom: " + werr)
    else:
        work, warnings = wdata
        parts.append(format_work(work, now))
        parts.extend(_warning_lines(warnings))
    if eerr:
        parts.append("Couldn't fetch emails: " + eerr)
    else:
        parts.append(format_emails(*edata))
    return "\n".join(parts)


def reply_email():
    data, err = get_emails()
    if err:
        return "Couldn't fetch emails: " + err
    emails, has_more = data
    if not emails:
        return "No unread emails in your inbox. Inbox zero!"
    return format_emails(emails, has_more)


def reply_classroom():
    data, err = get_work()
    if err:
        return "Couldn't fetch Classroom: " + err
    work, warnings = data
    return "\n".join([format_work(work, datetime.datetime.now())] + _warning_lines(warnings))


def ask_ai(text):
    context = None
    if commands.wants_context(text):
        edata, _ = get_emails(CACHE_TTL)
        wdata, _ = get_work(CACHE_TTL)
        if edata or wdata:
            context = build_context(
                edata[0] if edata else None,
                wdata[0] if wdata else None,
                datetime.datetime.now(),
            )
    try:
        return _conversation.ask(_model, text, context)
    except brain.BrainError as e:
        if e.kind == "offline":
            return ("Ollama isn't running, so I only know my built-in shortcuts.\n"
                    "Start the Ollama app (or run: ollama serve). Not installed? "
                    + platform_utils.ollama_install_hint())
        if e.kind == "model_missing":
            return f"{e}\nThen ask me again!"
        if e.kind == "timeout":
            return ("The AI took too long; the model may still be loading. Try again in a "
                    "moment, or use a smaller model (set JARVIS_MODEL).")
        return f"My brain hiccuped: {e}"


def status_report():
    lines = ["--- Jarvis status ---"]
    online = brain.is_ollama_online()
    lines.append(f"Local AI (Ollama): {'online' if online else 'OFFLINE'}")
    if online:
        ok = brain.model_available(_model)
        lines.append(f"Using model: {_model}" + ("" if ok else f"  (NOT INSTALLED: ollama pull {_model})"))
    ok, msg = auth.check_credentials()
    lines.append("Google account: " + ("connected" if ok else "NOT CONNECTED - " + msg))
    ok, name, err = voice.probe_tts()
    lines.append("Voice output: " + (name if ok else f"UNAVAILABLE ({err})"))
    return "\n".join(lines)


def handle(text):
    action = commands.route(text)
    if action == "quit":
        voice.say("Shutting down. See you soon!")
        voice.wait_for_speech(5)
        sys.exit(0)
    if action == "status":
        return status_report()
    if action == "help":
        return HELP_TEXT
    if action == "email":
        return reply_email()
    if action == "classroom":
        return reply_classroom()
    if action == "briefing":
        return format_briefing()
    return ask_ai(text)


# --- Startup / loop ----------------------------------------------------------

def init():
    global _model
    auth.CRED_DIR.mkdir(exist_ok=True)
    print(ASCII_LOGO)
    if not auth.TOKEN_PATH.exists():
        print("\nGoogle isn't connected yet (needed for emails and Classroom).\n"
              "Follow docs/GOOGLE_SETUP.md, then run:  "
              + platform_utils.VENV_PY_REL + " setup_google.py")
    if brain.is_ollama_online():
        _model = brain.suggest_model()
        print(f"Ollama online. Using model: {_model}")
        if not brain.model_available(_model):
            print(f"Model not installed yet. Run:  ollama pull {_model}")
    else:
        print("Ollama not detected. Built-in shortcuts still work.")
    voice.say("Hello, I'm Jarvis. What do you need?")


def read_command():
    if voice.voice_in_enabled:
        try:
            heard = voice.listen()
        except voice.VoiceInputError as e:
            print(f"[voice] {e}")
            if e.kind == "mic":
                voice.voice_in_enabled = False
                print("[voice] Voice input is off for this session; type instead.")
            heard = None
        if heard:
            print(f"You: {heard}")
            return heard
        return input("Type it instead (or press Enter to listen again): ").strip()
    return input("You: ").strip()


def main():
    platform_utils.make_console_utf8()
    args = sys.argv[1:]
    voice.voice_in_enabled = "--voice" in args
    if "--setup" in args:
        try:
            auth.get_credentials(interactive=True)
            print("Google connected.")
        except Exception as e:  # noqa: BLE001
            print("Google setup failed:", e)
        return
    init()
    while True:
        try:
            command = read_command()
            if not command:
                continue
            reply = handle(command)
            voice.say(reply, spoken=commands.speakable(reply))
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        except Exception as e:  # noqa: BLE001
            print("Unexpected error:", e)
            if os.environ.get("JARVIS_DEBUG"):
                traceback.print_exc()


if __name__ == "__main__":
    main()
