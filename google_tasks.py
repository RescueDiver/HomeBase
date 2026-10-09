import argparse
import re

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


BASE_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = BASE_DIR / "private"

DEFAULT_TOKEN_FILE = PRIVATE_DIR / "tasks_token.json"
CREDENTIALS_FILE = PRIVATE_DIR / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/tasks.readonly"
]


def safe_account_slug(account_name):
    slug = re.sub(
        r"[^a-z0-9]+",
        "_",
        account_name.strip().lower(),
    ).strip("_")

    if not slug:
        raise ValueError(
            "Account name must contain letters or numbers."
        )

    return slug


def token_file_for_account(
    account_name=None,
):
    if not account_name:
        return DEFAULT_TOKEN_FILE

    return (
        PRIVATE_DIR
        / f"tasks_token_{safe_account_slug(account_name)}.json"
    )


def get_google_tasks_service(
    allow_login=False,
    token_file=None,
):
    token_file = (
        Path(token_file)
        if token_file
        else DEFAULT_TOKEN_FILE
    )

    credentials = None

    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(
            token_file,
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
            if not allow_login:
                raise RuntimeError(
                    "Google Tasks is not authorized for this account."
                )

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

        token_file.write_text(
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


def get_all_open_tasks(
    allow_login=False,
    token_file=None,
    account_name="Primary",
):
    service = get_google_tasks_service(
        allow_login=allow_login,
        token_file=token_file,
    )

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
                    "account_name": account_name,
                    "list_id": task_list_id,
                    "list_title": task_list_title,
                    "task": task,
                }
            )

    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Authorize and test Google Tasks accounts for Marvin."
    )

    parser.add_argument(
        "--account",
        help=(
            "Account label. Example: "
            "python google_tasks.py --account Amber"
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    account_name = (
        args.account.strip()
        if args.account
        else "Primary"
    )

    token_file = token_file_for_account(
        args.account
    )

    items = get_all_open_tasks(
        allow_login=True,
        token_file=token_file,
        account_name=account_name,
    )

    print()
    print("=" * 60)
    print(
        f"MARVIN - GOOGLE TASKS - "
        f"{account_name.upper()}"
    )
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
    print(
        f"Token file: {token_file.name}"
    )


if __name__ == "__main__":
    main()
