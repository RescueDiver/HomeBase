from datetime import datetime

from google_tasks import get_all_open_tasks


MAX_DISPLAY_TASKS = 12


def format_due_date(due_text):
    if not due_text:
        return ""

    try:
        due_date = datetime.fromisoformat(
            due_text.replace(
                "Z",
                "+00:00",
            )
        )

        return due_date.strftime(
            "%b %d"
        ).replace(
            " 0",
            " ",
        )

    except ValueError:
        return ""


def task_sort_key(item):
    due_text = item["task"].get(
        "due"
    )

    return (
        0 if due_text else 1,
        due_text or "",
        item["list_title"].lower(),
        item["task"].get(
            "title",
            "",
        ).lower(),
    )


def get_marvin_tasks():
    raw_tasks = get_all_open_tasks()

    raw_tasks.sort(
        key=task_sort_key
    )

    display_tasks = []

    for item in raw_tasks[
        :MAX_DISPLAY_TASKS
    ]:
        task = item["task"]

        display_tasks.append(
            {
                "id": task.get("id"),
                "title": task.get(
                    "title",
                    "(No title)",
                ),
                "list_title": item[
                    "list_title"
                ],
                "due": format_due_date(
                    task.get("due")
                ),
                "notes": task.get(
                    "notes",
                    "",
                ),
            }
        )

    return {
        "tasks": display_tasks,
        "count": len(raw_tasks),
        "showing": len(display_tasks),
    }
