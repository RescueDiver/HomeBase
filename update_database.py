import sqlite3

connection = sqlite3.connect("data/homebase.db")

rows = connection.execute(
    """
    SELECT id, date, time, title, member, source, source_id
    FROM events
    WHERE source = 'google'
    ORDER BY date, time
    """
).fetchall()

for row in rows:
    print(row)

connection.close()