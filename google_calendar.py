from database import save_google_event
from datetime import datetime
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]


LOCAL_TIMEZONE = ZoneInfo("America/New_York")


def get_google_calendar_service():
    credentials = None

    try:
        credentials = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    except FileNotFoundError:
        pass

    if not credentials or not credentials.valid:

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            credentials = flow.run_local_server(port=0)

        with open("token.json", "w") as token_file:
            token_file.write(credentials.to_json())

    return build(
        "calendar",
        "v3",
        credentials=credentials
    )


def get_calendar_events(service, calendar_id):
    now = datetime.now(LOCAL_TIMEZONE)

    # Start at midnight on the first day
    # of the current month.
    month_start = now.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    events = []
    page_token = None

    while True:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=month_start.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=2500,
            pageToken=page_token
        ).execute()

        events.extend(
            result.get("items", [])
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

        local_datetime = event_datetime.astimezone(
            LOCAL_TIMEZONE
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


if __name__ == "__main__":
    service = get_google_calendar_service()

    family_calendar_id = (
        "family-calendar-id"
        "@group.calendar.google.com"
    )

    events = get_calendar_events(
        service,
        family_calendar_id
    )

    print()
    print("=" * 60)
    print("HOMEBASE - FAMILY CALENDAR SYNC")
    print("=" * 60)

    saved_count = 0

    for event in events:
        converted = convert_google_event(
            event
        )

        save_google_event(
            date=converted["date"],
            time=converted["time"],
            title=converted["title"],
            member="Family",
            source_id=converted["source_id"]
        )

        saved_count += 1

        print(
            converted["date"],
            converted["time"],
            "-",
            converted["title"]
        )

    print()
    print("=" * 60)
    print(
        f"Saved {saved_count} Google events."
    )
    print("=" * 60)