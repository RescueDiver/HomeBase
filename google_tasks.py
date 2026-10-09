from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


BASE_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = BASE_DIR / "private"

TOKEN_FILE = PRIVATE_DIR / "tasks_token.json"
CREDENTIALS_FILE = PRIVATE_DIR / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/tasks.readonly"
]


def get_google_tasks_service():
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

    if not credentials or not credentials.valid:
        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Google credentials file not found: "
                    f"{CREDENTIALS_FILE}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )

            credentials = flow.run_local_server(
                port=45158,
            )

        PRIVATE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return build(
        "tasks",
        "v1",
        credentials=credentials,
    )


def get_task_lists(service):
    task_lists = []
    page_token = None

    while True:
        result = service.tasklists().list(
            maxResults=100,
            pageToken=page_token,
        ).execute()

        task_lists.extend(
            result.get("items", [])
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return task_lists


def get_open_tasks(
    service,
    task_list_id,
):
    tasks = []
    page_token = None

    while True:
        result = service.tasks().list(
            tasklist=task_list_id,
            showCompleted=False,
            showDeleted=False,
            showHidden=False,
            maxResults=100,
            pageToken=page_token,
        ).execute()

        tasks.extend(
            result.get("items", [])
        )

        page_token = result.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return tasks


def get_all_open_tasks():
    service = get_google_tasks_service()

    results = []

    for task_list in get_task_lists(
        service
    ):
        task_list_id = task_list["id"]
        task_list_title = task_list.get(
            "title",
            "Tasks",
        )

        for task in get_open_tasks(
            service,
            task_list_id,
        ):
            if task.get("status") == "completed":
                continue

            results.append(
                {
                    "list_id": task_list_id,
                    "list_title": task_list_title,
                    "task": task,
                }
            )

    return results


def main():
    items = get_all_open_tasks()

    print()
    print("=" * 60)
    print("MARVIN - GOOGLE TASKS")
    print("=" * 60)

    if not items:
        print("No open tasks.")

    for item in items:
        task = item["task"]

        print(
            f"[{item['list_title']}] "
            f"{task.get('title', '(No title)')}"
        )

    print("=" * 60)
    print(
        f"{len(items)} open task(s)."
    )


if __name__ == "__main__":
    main()
