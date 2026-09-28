import json
import requests
import calendar

from datetime import datetime, timedelta
from database import ( get_events, add_event, delete_event, get_event, update_event,)
from flask import Flask, render_template, request, redirect

app = Flask(__name__)


def load_settings():
    with open("config/settings.json", "r") as file:
        return json.load(file)


def get_coordinates(location):
    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    if "results" not in data or not data["results"]:
        raise ValueError(f"Could not find weather location: {location}")

    result = data["results"][0]

    return {
        "name": result["name"],
        "state": result.get("admin1", ""),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "timezone": result["timezone"]
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

    if code in (51, 53, 55, 56, 57):
        return "Drizzle", "🌦️"

    if code in (61, 63, 65, 66, 67):
        return "Rain", "🌧️"

    if code in (71, 73, 75, 77):
        return "Snow", "🌨️"

    if code in (80, 81, 82):
        return "Showers", "🌧️"

    if code in (85, 86):
        return "Snow Showers", "🌨️"

    if code in (95, 96, 99):
        return "Thunderstorms", "⛈️"

    return "Unknown", "🌡️"


def get_weather(location, forecast_days=5):
    coordinates = get_coordinates(location)

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": coordinates["latitude"],
        "longitude": coordinates["longitude"],
        "current": "temperature_2m,weather_code,cloud_cover",
        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),
        "temperature_unit": "fahrenheit",
        "timezone": coordinates["timezone"],
        "forecast_days": forecast_days
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    current_description, current_icon = weather_description(
        data["current"]["weather_code"]
    )

    forecast = []

    for i, date_text in enumerate(data["daily"]["time"]):
        date = datetime.strptime(date_text, "%Y-%m-%d")

        description, icon = weather_description(
            data["daily"]["weather_code"][i]
        )

        if i == 0:
            day_name = "TODAY"
        else:
            day_name = date.strftime("%a").upper()

        forecast.append({
            "day": day_name,
            "icon": icon,
            "description": description,
            "high": round(data["daily"]["temperature_2m_max"][i]),
            "low": round(data["daily"]["temperature_2m_min"][i]),
            "rain": data["daily"]["precipitation_probability_max"][i]
        })

    return {
        "location": coordinates,
        "temperature": round(data["current"]["temperature_2m"]),
        "cloud_cover": data["current"]["cloud_cover"],
        "description": current_description,
        "icon": current_icon,
        "forecast": forecast
    }


def get_event_occurrences(
    start_date,
    repeat_type,
    repeat_until,
    year,
    month
):
    start = datetime.strptime(
        start_date,
        "%Y-%m-%d"
    ).date()

    if repeat_until:
        end = datetime.strptime(
            repeat_until,
            "%Y-%m-%d"
        ).date()
    else:
        end = None

    occurrences = []

    if repeat_type == "none":
        if start.year == year and start.month == month:
            occurrences.append(start)

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

        if current.year == year and current.month == month:
            occurrences.append(current)

        if repeat_type == "weekly":
            current += timedelta(days=7)

        elif repeat_type == "biweekly":
            current += timedelta(days=14)

        elif repeat_type == "monthly":
            next_month = current.month + 1
            next_year = current.year

            if next_month == 13:
                next_month = 1
                next_year += 1

            try:
                current = current.replace(
                    year=next_year,
                    month=next_month
                )

            except ValueError:
                test_month = next_month
                test_year = next_year

                while True:
                    test_month += 1

                    if test_month == 13:
                        test_month = 1
                        test_year += 1

                    try:
                        current = current.replace(
                            year=test_year,
                            month=test_month
                        )
                        break

                    except ValueError:
                        continue

        elif repeat_type == "yearly":
            next_year = current.year + 1

            try:
                current = current.replace(
                    year=next_year
                )

            except ValueError:
                while True:
                    next_year += 1

                    try:
                        current = current.replace(
                            year=next_year
                        )
                        break

                    except ValueError:
                        continue

        else:
            break

    return occurrences


@app.route("/")
def home():
    settings = load_settings()

    today = datetime.now()

    year = today.year
    month = today.month
    month_name = calendar.month_name[month]

    cal = calendar.Calendar(firstweekday=6)
    month_weeks = cal.monthdayscalendar(year, month)

    weather_settings = settings["weather"]

    weather = get_weather(
        weather_settings["location"],
        weather_settings["forecast_days"]
    )

    database_events = get_events()

    member_colors = {
        member["name"]: member["color"]
        for member in settings["calendar"]["members"]
    }

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
        repeat_until
    ) in database_events:

        occurrence_dates = get_event_occurrences(
            event_date,
            repeat_type or "none",
            repeat_until,
            year,
            month
        )

        for occurrence_date in occurrence_dates:
            event_day = occurrence_date.day

            if event_day not in events:
                events[event_day] = []

            events[event_day].append({
                "id": event_id,
                "time": event_time,
                "title": title,
                "member": member,
                "color": member_colors.get(
                    member,
                    "#FFFFFF"
                ),
                "source": source,
                "repeat_type": repeat_type or "none"
            })

    return render_template(
        "dashboard.html",
        year=year,
        month=month,
        month_name=month_name,
        month_weeks=month_weeks,
        today=today.day,
        weather=weather,
        events=events,
        members=settings["calendar"]["members"],
    )


@app.route("/add-event", methods=["GET", "POST"])
def add_event_page():
    settings = load_settings()
    members = settings["calendar"]["members"]

    if request.method == "POST":
        date = request.form["date"]

        hour = request.form["hour"]
        minute = request.form["minute"]
        ampm = request.form["ampm"]
        time = f"{hour}:{minute} {ampm}"

        title = request.form["title"].strip()
        member = request.form["member"]

        repeat_type = request.form.get(
            "repeat_type",
            "none"
        )

        repeat_until = (
            request.form.get("repeat_until")
            or None
        )

        valid_members = [
            person["name"]
            for person in members
        ]

        if member not in valid_members:
            return (
                f"Invalid family member: {member}. "
                "Please go back and select a valid person.",
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
        members=members
    )

@app.route("/delete-event/<int:event_id>", methods=["POST"])
def delete_event_page(event_id):
    delete_event(event_id)
    return redirect("/")

@app.route("/dev-calendar/<int:year>/<int:month>")
def dev_calendar(year, month):
    settings = load_settings()

    if month < 1 or month > 12:
        return "Invalid month", 400

    month_name = calendar.month_name[month]

    cal = calendar.Calendar(firstweekday=6)
    month_weeks = cal.monthdayscalendar(year, month)

    database_events = get_events()

    member_colors = {
        member["name"]: member["color"]
        for member in settings["calendar"]["members"]
    }

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
        repeat_until
    ) in database_events:

        occurrence_dates = get_event_occurrences(
            event_date,
            repeat_type or "none",
            repeat_until,
            year,
            month
        )

        for occurrence_date in occurrence_dates:
            event_day = occurrence_date.day

            if event_day not in events:
                events[event_day] = []

            events[event_day].append({
                "id": event_id,
                "time": event_time,
                "title": title,
                "member": member,
                "color": member_colors.get(member, "#FFFFFF"),
                "source": source,
                "repeat_type": repeat_type or "none"
            })

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
        members=settings["calendar"]["members"],
        previous_year=previous_year,
        previous_month=previous_month,
        next_year=next_year,
        next_month=next_month,
    )



if __name__ == "__main__":
    app.run(debug=True)