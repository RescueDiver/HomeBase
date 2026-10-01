import json
import subprocess
import sys
import time
import webbrowser

from pathlib import Path
from threading import Timer

import requests

from app import (
    app,
    get_marvin_shopping_list,
    get_weather,
)

from refresh_manager import (
    RefreshFailure,
    refresh_manager,
)


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


def refresh_calendar():
    result = subprocess.run(
        [
            sys.executable,
            str(GOOGLE_SYNC_FILE),
        ],
        cwd=BASE_DIR,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Google Calendar sync failed."
        )

    return True


def refresh_shopping():
    shopping = get_marvin_shopping_list()

    if not shopping["live"]:
        raise RefreshFailure(
            "Home Assistant shopping list "
            "is unavailable.",
            result=shopping,
        )

    return shopping


def refresh_weather():
    settings = load_settings()

    weather_settings = settings[
        "weather"
    ]

    return get_weather(
        weather_settings["location"],
        weather_settings["forecast_days"],
    )


def configure_refresh_system(
    settings
):
    refresh_settings = settings.get(
        "refresh",
        {}
    )

    refresh_manager.register(
        "Shopping List",
        refresh_settings.get(
            "shopping",
            30
        ),
        refresh_shopping,
    )

    refresh_manager.register(
        "Calendar",
        refresh_settings.get(
            "calendar",
            60
        ),
        refresh_calendar,
    )

    refresh_manager.register(
        "Weather",
        refresh_settings.get(
            "weather",
            600
        ),
        refresh_weather,
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

    configure_refresh_system(
        settings
    )

    refresh_manager.start()

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