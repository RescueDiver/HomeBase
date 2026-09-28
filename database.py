import sqlite3

DATABASE = "data/homebase.db"


def ensure_event_columns(connection):
    """
    Make sure the events table has the columns needed
    for recurring manual events.
    """

    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(events)").fetchall()
    }

    if "repeat_type" not in columns:
        connection.execute(
            """
            ALTER TABLE events
            ADD COLUMN repeat_type TEXT DEFAULT 'none'
            """
        )

    if "repeat_until" not in columns:
        connection.execute(
            """
            ALTER TABLE events
            ADD COLUMN repeat_until TEXT
            """
        )

    connection.commit()


def get_events():
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    rows = connection.execute(
        """
        SELECT
            id,
            date,
            time,
            title,
            member,
            source,
            source_id,
            repeat_type,
            repeat_until
        FROM events
        ORDER BY date, time
        """
    ).fetchall()

    connection.close()

    return rows


def get_event(event_id):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    event = connection.execute(
        """
        SELECT
            id,
            date,
            time,
            title,
            member,
            source,
            source_id,
            repeat_type,
            repeat_until
        FROM events
        WHERE id = ?
        """,
        (event_id,)
    ).fetchone()

    connection.close()

    return event


def add_event(
    date,
    time,
    title,
    member,
    repeat_type="none",
    repeat_until=None
):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    connection.execute(
        """
        INSERT INTO events
        (
            date,
            time,
            title,
            member,
            source,
            repeat_type,
            repeat_until
        )
        VALUES (?, ?, ?, ?, 'local', ?, ?)
        """,
        (
            date,
            time,
            title,
            member,
            repeat_type,
            repeat_until
        )
    )

    connection.commit()
    connection.close()


def delete_event(event_id):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    connection.execute(
        """
        DELETE FROM events
        WHERE id = ?
        AND source = 'local'
        """,
        (event_id,)
    )

    connection.commit()
    connection.close()


def save_google_event(
    date,
    time,
    title,
    member,
    source_id
):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    existing_event = connection.execute(
        """
        SELECT id
        FROM events
        WHERE source = 'google'
        AND source_id = ?
        """,
        (source_id,)
    ).fetchone()

    if existing_event:
        connection.execute(
            """
            UPDATE events
            SET
                date = ?,
                time = ?,
                title = ?,
                member = ?
            WHERE id = ?
            """,
            (
                date,
                time,
                title,
                member,
                existing_event[0]
            )
        )

    else:
        connection.execute(
            """
            INSERT INTO events
            (
                date,
                time,
                title,
                member,
                source,
                source_id,
                repeat_type
            )
            VALUES (?, ?, ?, ?, 'google', ?, 'none')
            """,
            (
                date,
                time,
                title,
                member,
                source_id
            )
        )

def update_event(
    event_id,
    date,
    time,
    title,
    member,
    repeat_type="none",
    repeat_until=None
    ):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    connection.execute(
        """
        UPDATE events
        SET
            date = ?,
            time = ?,
            title = ?,
            member = ?,
            repeat_type = ?,
            repeat_until = ?
        WHERE id = ?
        AND source = 'local'
        """,
        (
            date,
            time,
            title,
            member,
            repeat_type,
            repeat_until,
            event_id
        )
    )

def get_event(event_id):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    event = connection.execute(
        """
        SELECT
            id,
            date,
            time,
            title,
            member,
            source,
            source_id,
            repeat_type,
            repeat_until
        FROM events
        WHERE id = ?
        """,
        (event_id,)
    ).fetchone()

    connection.close()

    return event

def update_event(
        event_id,
        date,
        time,
        title,
        member,
        repeat_type="none",
        repeat_until=None
):
    connection = sqlite3.connect(DATABASE, timeout=10)

    ensure_event_columns(connection)

    connection.execute(
        """
        UPDATE events
        SET
            date = ?,
            time = ?,
            title = ?,
            member = ?,
            repeat_type = ?,
            repeat_until = ?
        WHERE id = ?
        AND source = 'local'
        """,
        (
            date,
            time,
            title,
            member,
            repeat_type,
            repeat_until,
            event_id
        )
    )

    connection.commit()
    connection.close()
