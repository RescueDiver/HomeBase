from database import get_events


def main():
    """
    Print Google Calendar events currently stored
    in the HomeBase database.
    """
    events = get_events()

    google_events = [
        event
        for event in events
        if event[5] == "google"
    ]

    if not google_events:
        print("No Google events found.")
        return

    print()
    print("=" * 60)
    print("HOMEBASE - STORED GOOGLE EVENTS")
    print("=" * 60)

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
    ) in google_events:

        print(
            f"{event_id}: "
            f"{event_date} "
            f"{event_time} - "
            f"{title} | "
            f"Member: {member}"
        )

    print()

    print(
        f"Total Google events: "
        f"{len(google_events)}"
    )


if __name__ == "__main__":
    main()