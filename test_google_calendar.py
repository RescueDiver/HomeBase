from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly"
]


def get_credentials():
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

    return credentials


def main():
    credentials = get_credentials()

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )
    calendar_list = service.calendarList().list().execute()

    print()
    print("=" * 60)
    print("CALENDARS MARVIN CAN SEE")
    print("=" * 60)

    for google_calendar in calendar_list.get("items", []):
        print(
            google_calendar.get("summary"),
            "-",
            google_calendar.get("id")
        )

    print()
    now = datetime.now(timezone.utc).isoformat()

    result = service.events().list(
        calendarId="family-calendar-id",
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = result.get("items", [])

    print()
    print("=" * 60)
    print("MARVIN - GOOGLE CALENDAR TEST")
    print("=" * 60)

    if not events:
        print("No upcoming events found.")
        return

    for event in events:
        start = event["start"].get(
            "dateTime",
            event["start"].get("date")
        )

        print(start, "-", event.get("summary", "(No title)"))


if __name__ == "__main__":
    main()