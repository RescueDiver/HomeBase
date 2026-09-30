import sqlite3
from contextlib import contextmanager

DATABASE = "data/homebase.db"

EVENT_COLUMNS = """
    id,
    date,
    time,
    title,
    member,
    source,
    source_id,
    repeat_type,
    repeat_until
"""


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


@contextmanager
def get_connection():
    """
    Open a database connection with the events table migrated,
    commit on success, and always close it (even on errors).
    """

    connection = sqlite3.connect(DATABASE, timeout=10)

    try:
        ensure_event_columns(connection)
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_events():
    with get_connection() as connection:
        return connection.execute(
            f"""
            SELECT {EVENT_COLUMNS}
            FROM events
            ORDER BY date, time
            """
        ).fetchall()


def get_event(event_id):
    with get_connection() as connection:
        return connection.execute(
            f"""
            SELECT {EVENT_COLUMNS}
            FROM events
            WHERE id = ?
            """,
            (event_id,)
        ).fetchone()


def add_event(
        date,
        time,
        title,
        member,
        repeat_type="none",
        repeat_until=None
):
    with get_connection() as connection:
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


def update_event(
        event_id,
        date,
        time,
        title,
        member,
        repeat_type="none",
        repeat_until=None
):
    with get_connection() as connection:
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


def delete_event(event_id):
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM events
            WHERE id = ?
            AND source = 'local'
            """,
            (event_id,)
        )


def save_google_event(
        date,
        time,
        title,
        member,
        source_id
):
    with get_connection() as connection:
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


def initialize_database():
    connection = sqlite3.connect(DATABASE, timeout=10)

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT,
                title TEXT NOT NULL,
                member TEXT,
                source TEXT DEFAULT 'local',
                source_id TEXT,
                repeat_type TEXT DEFAULT 'none',
                repeat_until TEXT
            )
            """
        )

        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
