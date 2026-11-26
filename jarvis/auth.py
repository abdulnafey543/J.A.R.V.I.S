import os
import pathlib

import platform_utils

BASE_DIR = pathlib.Path(__file__).resolve().parent
CRED_DIR = BASE_DIR / "credentials"
CLIENT_SECRET = CRED_DIR / "client_secret.json"
TOKEN_PATH = CRED_DIR / "token.json"

# Read-only scopes only: Jarvis can never send, delete or change anything.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
]


class AuthError(Exception):
    """Google login is missing, expired or revoked. The message says what to do."""


def _login_cmd():
    return f"{platform_utils.VENV_PY_REL} setup_google.py"


def _save(creds):
    """Write token.json readable only by the owner (set at creation, no race)."""
    CRED_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(TOKEN_PATH), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    try:
        os.chmod(TOKEN_PATH, 0o600)
    except OSError:
        pass


def get_credentials(interactive=False):
    """Return valid Google credentials.

    interactive=False (normal use) never opens a browser: it raises AuthError
    with instructions instead. setup_google.py passes interactive=True.
    """
    if not TOKEN_PATH.exists():
        if not interactive:
            raise AuthError(f"Not logged in to Google. Run:  {_login_cmd()}")
        if not CLIENT_SECRET.exists():
            raise AuthError(
                f"client_secret.json not found. Put it in: {CRED_DIR} "
                "(see docs/GOOGLE_SETUP.md)"
            )
    from google.auth.exceptions import RefreshError, TransportError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except (ValueError, OSError) as e:
            if not interactive:
                raise AuthError(f"token.json is unreadable ({e}). Run:  {_login_cmd()}")
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save(creds)
            return creds
        except TransportError as e:
            raise AuthError(f"Couldn't reach Google to refresh your login: {e}")
        except RefreshError as e:
            if not interactive:
                raise AuthError(
                    f"Your Google login expired or was revoked ({e}). Run:  {_login_cmd()}\n"
                    "Tip: if your Google Cloud app is in 'Testing' mode, logins expire "
                    "every 7 days (see docs/GOOGLE_SETUP.md)."
                )
    if not interactive:
        raise AuthError(f"Google login is no longer valid. Run:  {_login_cmd()}")
    if not CLIENT_SECRET.exists():
        raise AuthError(f"client_secret.json not found. Put it in: {CRED_DIR}")
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    _save(creds)
    print("\nLogin successful. Token saved to " + str(TOKEN_PATH))
    return creds


def check_credentials():
    """Non-interactive health check. Returns (ok, message)."""
    try:
        get_credentials(interactive=False)
        return True, "connected"
    except AuthError as e:
        return False, str(e)
    except ImportError:
        return False, f"Google packages not installed. Run:  {platform_utils.PY_CMD} setup.py"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def gmail_service():
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=get_credentials(), cache_discovery=False)


def classroom_service():
    from googleapiclient.discovery import build
    return build("classroom", "v1", credentials=get_credentials(), cache_discovery=False)
