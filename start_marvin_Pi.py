import json
import subprocess
import sys

from pathlib import Path

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
        encoding="utf-8",
    ) as file:
        return json.load(file)


def home_assistant_is_ready(
    url,
    token,
):
    """
    Check whether Home Assistant is reachable.

    On Raspberry Pi, Marvin does NOT try to
    start VMware or manage the Home Assistant VM.
    It only checks whether Home Assistant is available.
    """
    try:
        response = requests.get(
            f"{url.rstrip('/')}/api/",
            headers={
                "Authorization": (
                    f"Bearer {token}"
                )
            },
            timeout=5,
        )

        return response.status_code == 200

    except requests.RequestException:
        return False


def check_home_assistant(
    settings,
):
    home_assistant = settings.get(
        "home_assistant",
        {},
    )

    url = home_assistant.get(
        "url"
    )

    token = home_assistant.get(
        "token"
    )

    print()
    print("=" * 60)
    print("MARVIN - HOME ASSISTANT")
    print("=" * 60)

    if not url or not token:
        print(
            "Home Assistant settings missing."
        )
        return False

    if home_assistant_is_ready(
        url,
        token,
    ):
        print(
            "Home Assistant is online."
        )
        return True

    print(
        "Home Assistant is unavailable."
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
    shopping = (
        get_marvin_shopping_list()
    )

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
        weather_settings[
            "forecast_days"
        ],
    )


def configure_refresh_system(
    settings,
):
    refresh_settings = settings.get(
        "refresh",
        {},
    )

    refresh_manager.register(
        "Shopping List",
        refresh_settings.get(
            "shopping",
            30,
        ),
        refresh_shopping,
    )

    refresh_manager.register(
        "Calendar",
        refresh_settings.get(
            "calendar",
            60,
        ),
        refresh_calendar,
    )

    refresh_manager.register(
        "Weather",
        refresh_settings.get(
            "weather",
            600,
        ),
        refresh_weather,
    )


def start_marvin():
    settings = load_settings()

    print()
    print("=" * 60)
    print("MARVIN PI STARTING")
    print("=" * 60)

    check_home_assistant(
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

    print(
        "Network address:"
    )

    print(
        "http://0.0.0.0:5000"
    )

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    start_marvin()