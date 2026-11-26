# Security

## Protecting your Google credentials

JARVIS keeps two secret files in `credentials/`:

| File | What it is | If it leaks |
|---|---|---|
| `client_secret.json` | identifies *your* Google Cloud app | rotate it in Google Cloud Console |
| `token.json` | lets JARVIS read **your** mail and Classroom | revoke it (below) |

- Both are git-ignored. **Never** commit, email or screenshot them. Check with `git status` before pushing.
- JARVIS writes `token.json` readable only by you (mode 600 on Linux). On Windows it lives in
  your user profile folder; don't place the project in a shared folder.
- **Revoke access any time:** <https://myaccount.google.com/permissions> -> JARVIS -> Remove access. Then delete `token.json`.
- JARVIS only requests **read-only** scopes (`gmail.readonly` and Classroom `*.readonly`). It cannot send, delete or modify anything.
- If you accidentally push a secret: revoke it first, then rewrite history. Deleting the file in a later commit is not enough.

## Untrusted content

Email subjects and Classroom titles are written by other people. JARVIS sanitises them and tells
the local AI to treat them as data, not instructions. This reduces, but cannot completely
eliminate, prompt-injection risk with small models. JARVIS has no tools that can act on your
behalf, so the worst case is a misleading summary.

## Voice privacy

Microphone input uses Google's online speech recognition (audio is uploaded). Use typing mode
(the default) if that matters to you.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository (Security tab -> Report a vulnerability)
rather than a public issue.
