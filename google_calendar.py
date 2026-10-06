import json
import sqlite3

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from database import save_google_event


BASE_DIR = Path(__file__).resolve().parent
DATABASE_FILE = BASE_DIR / "data" / "homebase.db"

CONFIG_DIR = BASE_DIR / "config"
PRIVATE_DIR = BASE_DIR / "private"

PRIVATE_SETTINGS_FILE = CONFIG_DIR / "settings.local.json"
EXAMPLE_SETTINGS_FILE = CONFIG_DIR / "settings.example.json"

TOKEN_FILE = PRIVATE_DIR / "token.json"
CREDENTIALS_FILE = PRIVATE_DIR / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]

LOCAL_TIMEZONE = ZoneInfo("America/New_York")

HOLIDAY_CALENDAR_ID = (
    "en.usa#holiday@group.v.calendar.google.com"
)


def load_settings():
    """
    Load private local settings when available.

    Fall back to the GitHub-safe example settings
    if the private file does not exist.
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


def get_google_calendar_service():
    credentials = None

    if TOKEN_FILE.exists():
        credentials = (
            Credentials.from_authorized_user_file(
                TOKEN_FILE,
                SCOPES
            )
        )

    if not credentials or not credentials.valid:

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())

        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Google credentials file not found: "
                    f"{CREDENTIALS_FILE}"
                )

            flow = (
                InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE,
                    SCOPES
                )
            )

            credentials = flow.run_local_server(
                port=0
            )

        PRIVATE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8"
        )

    return build(
        "calendar",
        "v3",
        credentials=credentials
    )


def get_calendar_events(
    service,
    calendar_id
):
    now = datetime.now(
        LOCAL_TIMEZONE
    )

    month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    sync_end = (
        month_start
        + timedelta(days=370)
    )

    events = []
    page_token = None

    while True:

        result = service.events().list(
            calendarId=calendar_id,
            timeMin=month_start.isoformat(),
            timeMax=sync_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=2500,
            pageToken=page_token
        ).execute()

        events.extend(
            result.get(
                "items",
                []
            )
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return events


def convert_google_event(event):
    start = event["start"]

    if "dateTime" in start:

        event_datetime = datetime.fromisoformat(
            start["dateTime"].replace(
                "Z",
                "+00:00"
            )
        )

        local_datetime = (
            event_datetime.astimezone(
                LOCAL_TIMEZONE
            )
        )

        date = local_datetime.strftime(
            "%Y-%m-%d"
        )

        time = local_datetime.strftime(
            "%I:%M %p"
        ).lstrip("0")

    else:
        date = start["date"]
        time = ""

    return {
        "source_id": event["id"],
        "date": date,
        "time": time,
        "title": event.get(
            "summary",
            "(No title)"
        )
    }


def get_member_for_google_event(
    event,
    google_settings
):
    color_id = event.get(
        "colorId"
    )

    creator_email = (
        event.get(
            "creator",
            {}
        )
        .get(
            "email",
            ""
        )
        .lower()
    )

    title = event.get(
        "summary",
        ""
    ).lower()

    school_keywords = [
        "no school",
        "early dismissal",
        "christmas break",
        "last day of school",
        "spring break",
        "first day of school",
    ]

    if any(
        keyword in title
        for keyword in school_keywords
    ):
        return "Family"

    color_members = google_settings.get(
        "color_members",
        {}
    )

    if color_id in color_members:
        return color_members[
            color_id
        ]

    creator_members = google_settings.get(
        "creator_members",
        {}
    )

    if creator_email in creator_members:
        return creator_members[
            creator_email
        ]

    return "Family"


def sync_calendar(
    service,
    calendar_id,
    calendar_name,
    google_settings,
    force_member=None
):
    events = get_calendar_events(
        service,
        calendar_id
    )

    print()
    print("=" * 60)

    print(
        f"HOMEBASE - "
        f"{calendar_name.upper()} SYNC"
    )

    print("=" * 60)

    saved_count = 0

    for event in events:

        converted = convert_google_event(
            event
        )

        if force_member:
            member = force_member

        else:
            member = (
                get_member_for_google_event(
                    event,
                    google_settings
                )
            )

        save_google_event(
            date=converted["date"],
            time=converted["time"],
            title=converted["title"],
            member=member,
            source_id=converted["source_id"]
        )

        saved_count += 1

        print(
            converted["date"],
            converted["time"],
            "-",
            converted["title"],
            "| Member:",
            member
        )

    print()
    print("=" * 60)

    print(
        f"Saved {saved_count} "
        f"{calendar_name} events."
    )

    print("=" * 60)

    return saved_count


def remove_stale_google_events(
    service,
    calendar_ids,
):
    """
    Remove Google events from Marvin's database
    that no longer exist in Google Calendar.

    Local Marvin events are never touched.
    """

    valid_source_ids = set()

    for calendar_id in calendar_ids:
        events = get_calendar_events(
            service,
            calendar_id,
        )

        for event in events:
            event_id = event.get("id")

            if event_id:
                valid_source_ids.add(event_id)

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    try:
        cursor = connection.cursor()

        stored_events = cursor.execute(
            """
            SELECT id, source_id
            FROM events
            WHERE source = 'google'
            """
        ).fetchall()

        stale_ids = []

        for event_id, source_id in stored_events:
            if source_id not in valid_source_ids:
                stale_ids.append(event_id)

        for event_id in stale_ids:
            cursor.execute(
                """
                DELETE FROM events
                WHERE id = ?
                AND source = 'google'
                """,
                (event_id,),
            )

        connection.commit()

    finally:
        connection.close()

    print()
    print("=" * 60)
    print(
        f"Removed {len(stale_ids)} stale "
        f"Google Calendar events."
    )
    print("=" * 60)


def main():
    settings = load_settings()

    google_settings = settings.get(
        "google_calendar",
        {}
    )

    family_calendar_id = (
        google_settings.get(
            "family_calendar_id"
        )
    )

    dinner_calendar_id = (
        google_settings.get(
            "dinner_calendar_id"
        )
    )

    if not family_calendar_id:
        raise ValueError(
            "Missing google_calendar.family_calendar_id "
            "in config/settings.local.json"
        )

    if not dinner_calendar_id:
        raise ValueError(
            "Missing google_calendar.dinner_calendar_id "
            "in config/settings.local.json"
        )

    service = (
        get_google_calendar_service()
    )

    family_count = sync_calendar(
        service=service,
        calendar_id=family_calendar_id,
        calendar_name="Family Calendar",
        google_settings=google_settings
    )

    holiday_count = sync_calendar(
        service=service,
        calendar_id=HOLIDAY_CALENDAR_ID,
        calendar_name="U.S. Holidays",
        google_settings=google_settings,
        force_member="Family"
    )
    dinner_count = sync_calendar(
        service=service,
        calendar_id=dinner_calendar_id,
        calendar_name="Dinner Menu",
        google_settings=google_settings,
        force_member="Dinner"
    )
    remove_stale_google_events(
        service,
        [
            family_calendar_id,
            dinner_calendar_id,
            HOLIDAY_CALENDAR_ID,
        ],
    )

    total_count = (
        family_count
        + dinner_count
        + holiday_count
    )

    print()
    print("=" * 60)

    print(
        f"TOTAL SAVED: "
        f"{total_count} Google events."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
