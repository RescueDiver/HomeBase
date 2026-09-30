from database import save_google_event
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]

LOCAL_TIMEZONE = ZoneInfo("America/New_York")

FAMILY_CALENDAR_ID = (
    "family-calendar-id"
    "@group.calendar.google.com"
)

HOLIDAY_CALENDAR_ID = (
    "en.usa#holiday@group.v.calendar.google.com"
)


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
            token_file.write(
                credentials.to_json()
            )

    return build(
        "calendar",
        "v3",
        credentials=credentials
    )


def get_calendar_events(service, calendar_id):
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

    sync_end = month_start + timedelta(
        days=370
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


def get_member_for_google_event(event):
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

    if color_id == "10":
        return "Person 3"

    if color_id == "11":
        return "Family"

    if color_id == "5":
        return "Family"

    if (
        creator_email
        == "user1@example.com"
    ):
        return "Person 1"

    if (
        creator_email
        == "user2@example.com"
    ):
        return "Person 2"

    return "Family"


def sync_calendar(
    service,
    calendar_id,
    calendar_name,
    force_member=None
):
    events = get_calendar_events(
        service,
        calendar_id
    )

    print()
    print("=" * 60)
    print(
        f"HOMEBASE - {calendar_name.upper()} SYNC"
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
                    event
                )
            )

        save_google_event(
            date=converted["date"],
            time=converted["time"],
            title=converted["title"],
            member=member,
            source_id=converted[
                "source_id"
            ]
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


if __name__ == "__main__":
    service = (
        get_google_calendar_service()
    )

    family_count = sync_calendar(
        service=service,
        calendar_id=FAMILY_CALENDAR_ID,
        calendar_name="Family Calendar"
    )

    holiday_count = sync_calendar(
        service=service,
        calendar_id=HOLIDAY_CALENDAR_ID,
        calendar_name="U.S. Holidays",
        force_member="Family"
    )

    total_count = (
        family_count
        + holiday_count
    )

    print()
    print("=" * 60)
    print(
        f"TOTAL SAVED: "
        f"{total_count} Google events."
    )
    print("=" * 60)