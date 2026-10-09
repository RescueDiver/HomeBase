import json

from datetime import date, datetime, timedelta
from pathlib import Path

from google_tasks import get_all_open_tasks


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"

PRIVATE_SETTINGS_FILE = CONFIG_DIR / "settings.local.json"
EXAMPLE_SETTINGS_FILE = CONFIG_DIR / "settings.example.json"

DEFAULT_MAX_DISPLAY_TASKS = 12


def load_task_settings():
    if PRIVATE_SETTINGS_FILE.exists():
        settings_file = PRIVATE_SETTINGS_FILE
    else:
        settings_file = EXAMPLE_SETTINGS_FILE

    try:
        with settings_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            settings = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    return settings.get(
        "google_tasks",
        {},
    )


def parse_due_date(due_text):
    if not due_text:
        return None

    try:
        return datetime.fromisoformat(
            due_text.replace(
                "Z",
                "+00:00",
            )
        ).date()

    except ValueError:
        return None


def format_due_date(due_text):
    due_date = parse_due_date(
        due_text
    )

    if due_date is None:
        return {
            "label": "",
            "status": "none",
        }

    today = date.today()

    if due_date < today:
        return {
            "label": (
                "OVERDUE "
                + due_date.strftime(
                    "%b %d"
                ).replace(
                    " 0",
                    " ",
                )
            ),
            "status": "overdue",
        }

    if due_date == today:
        return {
            "label": "TODAY",
            "status": "today",
        }

    if due_date == (
        today + timedelta(days=1)
    ):
        return {
            "label": "TOMORROW",
            "status": "tomorrow",
        }

    return {
        "label": due_date.strftime(
            "%b %d"
        ).replace(
            " 0",
            " ",
        ),
        "status": "future",
    }


def task_sort_key(item):
    due_date = parse_due_date(
        item["task"].get(
            "due"
        )
    )

    return (
        0 if due_date else 1,
        due_date or date.max,
        item["list_title"].lower(),
        item["task"].get(
            "title",
            "",
        ).lower(),
    )


def list_is_included(
    list_title,
    include_lists,
):
    if not include_lists:
        return True

    wanted = {
        name.strip().lower()
        for name in include_lists
        if name.strip()
    }

    return (
        list_title.strip().lower()
        in wanted
    )


def get_marvin_tasks():
    task_settings = load_task_settings()

    max_display = int(
        task_settings.get(
            "max_display",
            DEFAULT_MAX_DISPLAY_TASKS,
        )
    )

    include_lists = task_settings.get(
        "include_lists",
        [],
    )

    raw_tasks = [
        item
        for item in get_all_open_tasks()
        if list_is_included(
            item["list_title"],
            include_lists,
        )
    ]

    raw_tasks.sort(
        key=task_sort_key
    )

    display_tasks = []

    for item in raw_tasks[
        :max_display
    ]:
        task = item["task"]

        due = format_due_date(
            task.get("due")
        )

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
                "due": due["label"],
                "due_status": due[
                    "status"
                ],
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
