# Connecting Google (one time, about 10 minutes)

JARVIS needs a free "OAuth client" from Google Cloud so *you* can log in with your own account.

1. Go to <https://console.cloud.google.com/> and create a project (e.g. "JARVIS").
2. **APIs & Services -> Library**: enable the **Gmail API** and the **Google Classroom API**.
3. **APIs & Services -> OAuth consent screen**: choose **External**, fill in an app name and your email.
   Under **Test users**, add the Google account you'll log in with.
4. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID -> Desktop app**.
5. Click **Download JSON**, rename the file to exactly `client_secret.json`, and put it in the
   project's `credentials/` folder.
6. Log in:
   - Fedora: `.venv/bin/python setup_google.py`
   - Windows: `.venv\Scripts\python.exe setup_google.py`

   A browser opens. Google shows an "unverified app" warning because it's *your* app: choose
   **Advanced -> Go to JARVIS** and allow the read-only permissions.
7. Check: `python3 run.py --check` (Windows: `python run.py --check`).

## Good to know

- **"Testing" mode logins expire after 7 days.** JARVIS will tell you to log in again. To avoid
  this, set the consent screen's publishing status to **In production** (it stays private to you; Google
  just keeps showing the unverified-app warning).
- **School accounts:** many schools' Google Workspace admins block third-party apps. If login
  fails with "access blocked", ask your admin to allow the app, or use a personal account for Gmail.
- **Error 403 / "API not enabled":** repeat step 2 in the same project that created your client ID.
- Wrong account? Delete `credentials/token.json` and run step 6 again.
