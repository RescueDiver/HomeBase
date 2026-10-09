import json
import subprocess
import sys

from pathlib import Path

from app import (
    app,
    get_weather,
)

from refresh_manager import (
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