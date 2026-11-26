import sys

import auth
import platform_utils


def main():
    print("Google setup wizard for Jarvis")
    auth.CRED_DIR.mkdir(exist_ok=True)
    if not auth.CLIENT_SECRET.exists():
        print(
            "\nERROR: I couldn't find " + str(auth.CLIENT_SECRET) + "\n\n"
            "1) Follow docs/GOOGLE_SETUP.md to download your client_secret.json\n"
            "2) Put it in the folder:\n     " + str(auth.CRED_DIR) + "\n"
            "   (exact filename must be client_secret.json)\n"
            "3) Run this command again.\n"
        )
        sys.exit(1)
    print("\nOpening browser for login...")
    try:
        auth.get_credentials(interactive=True)
    except Exception as e:  # noqa: BLE001
        print("\nLogin failed: " + str(e))
        sys.exit(1)
    print("\nDone! Google is connected.")
    print("Test it: run  " + platform_utils.PY_CMD + " run.py  then ask about your emails or homework.")


if __name__ == "__main__":
    main()
