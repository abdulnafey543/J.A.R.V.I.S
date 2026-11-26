# Contributing

Thanks for helping! Quick rules:

1. **Run the tests** before opening a pull request:
   `python -m unittest discover -s tests -t . -v`
2. **Add a test** for every bug fix and feature. Tests use only the standard library and fake
   Google/Ollama/audio objects, so they need no accounts, microphone or internet.
3. **Keep it cross-platform.** Anything OS-specific goes in `platform_utils.py` (or is guarded by
   `IS_WINDOWS` / `IS_LINUX`) and needs a test for both branches.
4. **Never print or commit secrets.** `credentials/` is git-ignored; keep it that way.
5. **Keep Google access read-only.** Don't add write scopes without discussing it first.
6. **Errors must explain themselves:** say what went wrong *and* what the user should do.

CI runs on Windows and Linux (Python 3.10 and 3.12). Real-hardware checks (microphone, Google
login, Ollama) can't run in CI - mention in your PR which OS you tried it on.
