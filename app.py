import calendar
import json

from datetime import datetime, timedelta
from pathlib import Path

import requests

from flask import Flask, redirect, render_template, request

from database import (
    add_event,
    delete_event,
    get_event,
    get_events,
    update_event,
)

from refresh_manager import refresh_manager


app = Flask(__name__)


BASE_DIR = Path(__file__).resolve().parent

CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

PRIVATE_SETTINGS_FILE = (
    CONFIG_DIR / "settings.local.json"
)

EXAMPLE_SETTINGS_FILE = (
    CONFIG_DIR / "settings.example.json"
)



def load_settings():
    """
    Load private local settings when available.

    Fall back to the GitHub-safe example settings
    when private settings are unavailable.
    """
    if PRIVATE_SETTINGS_FILE.exists():
        settings_file = PRIVATE_SETTINGS_FILE
    else:
        settings_file = EXAMPLE_SETTINGS_FILE

    with settings_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def get_coordinates(location):
    url = (
        "https://geocoding-api.open-meteo.com/"
        "v1/search"
    )

    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("results"):
        raise ValueError(
            f"Could not find weather location: "
            f"{location}"
        )

    result = data["results"][0]

    return {
        "name": result["name"],
        "state": result.get(
            "admin1",
            ""
        ),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "timezone": result["timezone"],
    }


def weather_description(code):
    if code == 0:
        return "Sunny", "☀️"

    if code in (1, 2):
        return "Partly Cloudy", "🌤️"

    if code == 3:
        return "Cloudy", "☁️"

    if code in (45, 48):
        return "Foggy", "🌫️"

    if code in (
        51,
        53,
        55,
        56,
        57,
    ):
        return "Drizzle", "🌦️"

    if code in (
        61,
        63,
        65,
        66,
        67,
    ):
        return "Rain", "🌧️"

    if code in (
        71,
        73,
        75,
        77,
    ):
        return "Snow", "🌨️"

    if code in (
        80,
        81,
        82,
    ):
        return "Showers", "🌧️"

    if code in (
        85,
        86,
    ):
        return "Snow Showers", "🌨️"

    if code in (
        95,
        96,
        99,
    ):
        return "Thunderstorms", "⛈️"

    return "Unknown", "🌡️"


def get_weather(
    location,
    forecast_days=5
):
    coordinates = get_coordinates(
        location
    )

    url = (
        "https://api.open-meteo.com/"
        "v1/forecast"
    )

    params = {
        "latitude": coordinates[
            "latitude"
        ],
        "longitude": coordinates[
            "longitude"
        ],
        "current": (
            "temperature_2m,"
            "weather_code,"
            "cloud_cover"
        ),
        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "temperature_unit": "fahrenheit",
        "timezone": coordinates[
            "timezone"
        ],
        "forecast_days": forecast_days,
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    current_description, current_icon = (
        weather_description(
            data[
                "current"
            ][
                "weather_code"
            ]
        )
    )

    forecast = []

    for index, date_text in enumerate(
        data["daily"]["time"]
    ):
        date = datetime.strptime(
            date_text,
            "%Y-%m-%d",
        )

        description, icon = (
            weather_description(
                data[
                    "daily"
                ][
                    "weather_code"
                ][index]
            )
        )

        if index == 0:
            day_name = "TODAY"
        else:
            day_name = (
                date.strftime(
                    "%a"
                ).upper()
            )

        forecast.append(
            {
                "day": day_name,
                "icon": icon,
                "description": description,
                "high": round(
                    data[
                        "daily"
                    ][
                        "temperature_2m_max"
                    ][index]
                ),
                "low": round(
                    data[
                        "daily"
                    ][
                        "temperature_2m_min"
                    ][index]
                ),
                "rain": data[
                    "daily"
                ][
                    "precipitation_probability_max"
                ][index],
            }
        )

    return {
        "location": coordinates,
        "temperature": round(
            data[
                "current"
            ][
                "temperature_2m"
            ]
        ),
        "cloud_cover": data[
            "current"
        ][
            "cloud_cover"
        ],
        "description": (
            current_description
        ),
        "icon": current_icon,
        "forecast": forecast,
    }



def get_event_occurrences(
    start_date,
    repeat_type,
    repeat_until,
    year,
    month,
):
    start = datetime.strptime(
        start_date,
        "%Y-%m-%d",
    ).date()

    if repeat_until:
        end = datetime.strptime(
            repeat_until,
            "%Y-%m-%d",
        ).date()
    else:
        end = None

    occurrences = []

    if repeat_type == "none":
        if (
            start.year == year
            and start.month == month
        ):
            occurrences.append(
                start
            )

        return occurrences

    current = start

    while True:
        if end and current > end:
            break

        if (
            current.year > year
            or (
                current.year == year
                and current.month > month
            )
        ):
            break

        if (
            current.year == year
            and current.month == month
        ):
            occurrences.append(
                current
            )

        if repeat_type == "weekly":
            current += timedelta(
                days=7
            )

        elif repeat_type == "biweekly":
            current += timedelta(
                days=14
            )

        elif repeat_type == "monthly":
            next_month = (
                current.month + 1
            )

            next_year = (
                current.year
            )

            if next_month == 13:
                next_month = 1
                next_year += 1

            while True:
                try:
                    current = (
                        current.replace(
                            year=next_year,
                            month=next_month,
                        )
                    )

                    break

                except ValueError:
                    next_month += 1

                    if next_month == 13:
                        next_month = 1
                        next_year += 1

        elif repeat_type == "yearly":
            next_year = (
                current.year + 1
            )

            while True:
                try:
                    current = (
                        current.replace(
                            year=next_year
                        )
                    )

                    break

                except ValueError:
                    next_year += 1

        else:
            break

    return occurrences


def build_calendar_events(
    database_events,
    member_colors,
    year,
    month,
):
    """
    Convert database rows into the dictionary
    used by the calendar templates.
    """
    events = {}

    for (
        event_id,
        event_date,
        event_time,
        title,
        member,
        source,
        source_id,
        repeat_type,
        repeat_until,
    ) in database_events:

        occurrence_dates = (
            get_event_occurrences(
                event_date,
                repeat_type or "none",
                repeat_until,
                year,
                month,
            )
        )

        for occurrence_date in (
            occurrence_dates
        ):
            event_day = (
                occurrence_date.day
            )

            if event_day not in events:
                events[event_day] = []

            events[event_day].append(
                {
                    "id": event_id,
                    "time": event_time,
                    "title": title,
                    "member": member,
                    "color": (
                        member_colors.get(
                            member,
                            "#FFFFFF",
                        )
                    ),
                    "source": source,
                    "repeat_type": (
                        repeat_type
                        or "none"
                    ),
                }
            )

    return events


def get_member_colors(settings):
    return {
        member["name"]: member[
            "color"
        ]
        for member in settings[
            "calendar"
        ][
            "members"
        ]
    }


def split_event_time(event_time):
    """
    Convert a stored 12-hour event time into
    hour, minute, and AM/PM values for editing.
    """
    if not event_time:
        return 12, "00", "AM"

    try:
        time_part, ampm = (
            event_time.split()
        )

        hour_text, minute = (
            time_part.split(":")
        )

        return (
            int(hour_text),
            minute,
            ampm,
        )

    except ValueError:
        return 12, "00", "AM"


@app.route("/")
def home():
    settings = load_settings()

    today = datetime.now()

    year = today.year
    month = today.month

    month_name = calendar.month_name[
        month
    ]

    cal = calendar.Calendar(
        firstweekday=6
    )

    month_weeks = (
        cal.monthdayscalendar(
            year,
            month,
        )
    )

    weather_settings = (
        settings["weather"]
    )

    weather = refresh_manager.get_result(
        "Weather"
    )

    tasks = refresh_manager.get_result(
        "Tasks",
        {
            "tasks": [],
            "count": 0,
            "showing": 0,
        },
    )

    if weather is None:
        weather = {
            "location": {
                "name": weather_settings[
                    "location"
                ],
                "state": "",
            },
            "temperature": "--",
            "cloud_cover": "--",
            "description": "Unavailable",
            "icon": "🌡️",
            "forecast": [],
        }

    database_events = get_events()

    member_colors = (
        get_member_colors(
            settings
        )
    )

    events = build_calendar_events(
        database_events,
        member_colors,
        year,
        month,
    )


    refresh_status = {
        "calendar": refresh_manager.get_status(
            "Calendar"
        ),
        "weather": refresh_manager.get_status(
            "Weather"
        ),
        "tasks": refresh_manager.get_status(
            "Tasks"
        ),
    }

    return render_template(
        "dashboard.html",
        year=year,
        month=month,
        month_name=month_name,
        month_weeks=month_weeks,
        today=today.day,
        weather=weather,
        tasks=tasks,
        events=events,
        refresh_status=refresh_status,
        members=settings[
            "calendar"
        ][
            "members"
        ],
    )


@app.route(
    "/add-event",
    methods=["GET", "POST"],
)
def add_event_page():
    settings = load_settings()

    members = settings[
        "calendar"
    ][
        "members"
    ]

    if request.method == "POST":
        date = request.form[
            "date"
        ]

        hour = request.form[
            "hour"
        ]

        minute = request.form[
            "minute"
        ]

        ampm = request.form[
            "ampm"
        ]

        time = (
            f"{hour}:{minute} "
            f"{ampm}"
        )

        title = request.form[
            "title"
        ].strip()

        member = request.form[
            "member"
        ]

        repeat_type = (
            request.form.get(
                "repeat_type",
                "none",
            )
        )

        repeat_until = (
            request.form.get(
                "repeat_until"
            )
            or None
        )

        valid_members = [
            person["name"]
            for person in members
        ]

        if member not in valid_members:
            return (
                (
                    f"Invalid family member: "
                    f"{member}. "
                    "Please go back and select "
                    "a valid person."
                ),
                400,
            )

        add_event(
            date,
            time,
            title,
            member,
            repeat_type,
            repeat_until,
        )

        return redirect("/")

    return render_template(
        "add_event.html",
        members=members,
    )


@app.route(
    "/edit-event/<int:event_id>",
    methods=["GET", "POST"],
)
def edit_event_page(event_id):
    settings = load_settings()

    members = settings[
        "calendar"
    ][
        "members"
    ]

    event = get_event(
        event_id
    )

    if event is None:
        return (
            "Event not found",
            404
        )

    if event[5] != "local":
        return (
            "Google events cannot "
            "be edited here.",
            403,
        )

    if request.method == "POST":
        date = request.form[
            "date"
        ]

        hour = request.form[
            "hour"
        ]

        minute = request.form[
            "minute"
        ]

        ampm = request.form[
            "ampm"
        ]

        time = (
            f"{hour}:{minute} "
            f"{ampm}"
        )

        title = request.form[
            "title"
        ].strip()

        member = request.form[
            "member"
        ]

        repeat_type = (
            request.form.get(
                "repeat_type",
                "none",
            )
        )

        repeat_until = (
            request.form.get(
                "repeat_until"
            )
            or None
        )

        valid_members = [
            person["name"]
            for person in members
        ]

        if member not in (
            valid_members
        ):
            return (
                (
                    f"Invalid family member: "
                    f"{member}."
                ),
                400,
            )

        update_event(
            event_id,
            date,
            time,
            title,
            member,
            repeat_type,
            repeat_until,
        )

        return redirect("/")

    selected_hour, (
        selected_minute
    ), selected_ampm = (
        split_event_time(
            event[2]
        )
    )

    event_data = {
        "id": event[0],
        "date": event[1],
        "time": event[2],
        "title": event[3],
        "member": event[4],
        "source": event[5],
        "source_id": event[6],
        "repeat_type": (
            event[7] or "none"
        ),
        "repeat_until": event[8],
    }

    return render_template(
        "edit_event.html",
        event=event_data,
        members=members,
        selected_hour=(
            selected_hour
        ),
        selected_minute=(
            selected_minute
        ),
        selected_ampm=(
            selected_ampm
        ),
    )


@app.route(
    "/delete-event/<int:event_id>",
    methods=["POST"],
)
def delete_event_page(event_id):
    delete_event(
        event_id
    )

    return redirect("/")


@app.route(
    "/dev-calendar/"
    "<int:year>/<int:month>"
)
def dev_calendar(year, month):
    settings = load_settings()

    if month < 1 or month > 12:
        return (
            "Invalid month",
            400
        )

    month_name = calendar.month_name[
        month
    ]

    cal = calendar.Calendar(
        firstweekday=6
    )

    month_weeks = (
        cal.monthdayscalendar(
            year,
            month,
        )
    )

    database_events = get_events()

    member_colors = (
        get_member_colors(
            settings
        )
    )

    events = build_calendar_events(
        database_events,
        member_colors,
        year,
        month,
    )

    if month == 1:
        previous_year = year - 1
        previous_month = 12
    else:
        previous_year = year
        previous_month = month - 1

    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1

    return render_template(
        "dev_calendar.html",
        year=year,
        month=month,
        month_name=month_name,
        month_weeks=month_weeks,
        events=events,
        members=settings[
            "calendar"
        ][
            "members"
        ],
        previous_year=(
            previous_year
        ),
        previous_month=(
            previous_month
        ),
        next_year=next_year,
        next_month=next_month,
    )


if __name__ == "__main__":
    app.run(
        debug=True
    )