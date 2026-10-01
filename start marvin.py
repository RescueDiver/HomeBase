import json
import subprocess
import sys
import time
import webbrowser

from pathlib import Path
from threading import Timer

import requests

from app import app


BASE_DIR = Path(__file__).resolve().parent

SETTINGS_FILE = (
    BASE_DIR
    / "config"
    / "settings.local.json"
)

GOOGLE_SYNC_FILE = (
    BASE_DIR
    / "google_calendar.py"
)


def load_settings():
    with SETTINGS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def find_vmrun():
    """
    Find VMware's vmrun.exe.
    """
    possible_paths = [
        Path(
            r"C:\Program Files\VMware"
            r"\VMware Workstation\vmrun.exe"
        ),
        Path(
            r"C:\Program Files (x86)\VMware"
            r"\VMware Workstation\vmrun.exe"
        ),
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def home_assistant_is_ready(
    url,
    token
):
    """
    Check whether Home Assistant's API is reachable.
    """
    try:
        response = requests.get(
            f"{url.rstrip('/')}/api/",
            headers={
                "Authorization": (
                    f"Bearer {token}"
                )
            },
            timeout=3
        )

        return response.status_code == 200

    except requests.RequestException:
        return False


def start_home_assistant(
    settings
):
    """
    Start the VMware Home Assistant VM if needed.
    """
    home_assistant = settings.get(
        "home_assistant",
        {}
    )

    url = home_assistant.get("url")
    token = home_assistant.get("token")
    vmx_path = home_assistant.get(
        "vmx_path"
    )

    if not url or not token:
        print(
            "Home Assistant settings missing."
        )
        return False

    print()
    print("=" * 60)
    print("MARVIN - HOME ASSISTANT")
    print("=" * 60)

    if home_assistant_is_ready(
        url,
        token
    ):
        print(
            "Home Assistant is already running."
        )
        return True

    if not vmx_path:
        print(
            "No VMware VM path configured."
        )
        return False

    vmx_file = Path(vmx_path)

    if not vmx_file.exists():
        print(
            "Home Assistant VM not found:"
        )
        print(vmx_file)
        return False

    vmrun = find_vmrun()

    if vmrun is None:
        print(
            "VMware vmrun.exe was not found."
        )
        return False

    print(
        "Starting Home Assistant VM..."
    )

    result = subprocess.run(
        [
            str(vmrun),
            "start",
            str(vmx_file),
            "nogui",
        ],
        capture_output=True,
        text=True
    )

    if (
        result.returncode != 0
        and "already powered on"
        not in result.stderr.lower()
    ):
        print(
            "VMware reported:"
        )

        print(
            result.stderr.strip()
        )

    print(
        "Waiting for Home Assistant..."
    )

    timeout_seconds = 300
    check_interval = 5

    elapsed = 0

    while elapsed < timeout_seconds:

        if home_assistant_is_ready(
            url,
            token
        ):
            print(
                "Home Assistant is ready."
            )

            return True

        time.sleep(
            check_interval
        )

        elapsed += (
            check_interval
        )

        print(
            f"Waiting... "
            f"{elapsed} seconds"
        )

    print(
        "Home Assistant did not become "
        "ready within 5 minutes."
    )

    print(
        "Marvin will continue without it."
    )

    return False


def sync_google_calendar():
    """
    Run the Google Calendar synchronization.

    Marvin continues even if the sync fails.
    """
    print()
    print("=" * 60)
    print("MARVIN - GOOGLE CALENDAR")
    print("=" * 60)

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(GOOGLE_SYNC_FILE),
            ],
            cwd=BASE_DIR,
            check=False
        )

        if result.returncode == 0:
            print(
                "Google Calendar sync complete."
            )
        else:
            print(
                "Google Calendar sync failed."
            )

            print(
                "Marvin will use the events "
                "already stored locally."
            )

    except Exception as error:
        print(
            "Google Calendar sync error:"
        )

        print(error)

        print(
            "Marvin will continue."
        )


def open_dashboard():
    """
    Open Marvin in the default browser.
    """
    webbrowser.open(
        "http://127.0.0.1:5000"
    )


def start_marvin():
    settings = load_settings()

    print()
    print("=" * 60)
    print("MARVIN STARTING")
    print("=" * 60)

    start_home_assistant(
        settings
    )

    sync_google_calendar()

    print()
    print("=" * 60)
    print("MARVIN DASHBOARD")
    print("=" * 60)

    print(
        "Starting dashboard..."
    )

    Timer(
        2,
        open_dashboard
    ).start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    start_marvin()