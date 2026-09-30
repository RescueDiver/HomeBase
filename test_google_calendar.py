from datetime import datetime, timezone

from google_calendar import (
    get_google_calendar_service,
    load_settings,
)


def print_visible_calendars(service):
    """
    Print every Google Calendar Marvin can currently access.
    """
    calendar_list = (
        service.calendarList()
        .list()
        .execute()
    )

    print()
    print("=" * 60)
    print("CALENDARS MARVIN CAN SEE")
    print("=" * 60)

    calendars = calendar_list.get(
        "items",
        []
    )

    if not calendars:
        print("No calendars found.")
        return

    for google_calendar in calendars:
        name = google_calendar.get(
            "summary",
            "(No name)"
        )

        calendar_id = google_calendar.get(
            "id",
            "(No ID)"
        )

        print(
            f"{name} - {calendar_id}"
        )


def print_upcoming_family_events(
    service,
    family_calendar_id
):
    """
    Print the next ten events from the Family calendar.
    """
    now = datetime.now(
        timezone.utc
    ).isoformat()

    result = service.events().list(
        calendarId=family_calendar_id,
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = result.get(
        "items",
        []
    )

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
            event["start"].get(
                "date"
            )
        )

        title = event.get(
            "summary",
            "(No title)"
        )

        print(
            f"{start} - {title}"
        )


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

    if not family_calendar_id:
        raise ValueError(
            "Missing google_calendar.family_calendar_id "
            "in config/settings.local.json"
        )

    service = (
        get_google_calendar_service()
    )

    print_visible_calendars(
        service
    )

    print_upcoming_family_events(
        service,
        family_calendar_id
    )


if __name__ == "__main__":
    main()