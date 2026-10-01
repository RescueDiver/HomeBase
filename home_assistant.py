import json
import time

from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent

PRIVATE_SETTINGS_FILE = (
    BASE_DIR
    / "config"
    / "settings.local.json"
)


def load_settings():
    """
    Load HomeBase private local settings.
    """
    with PRIVATE_SETTINGS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def get_home_assistant_settings():
    """
    Return the Home Assistant configuration section.
    """
    settings = load_settings()

    home_assistant = settings.get(
        "home_assistant",
        {}
    )

    required_fields = [
        "url",
        "token",
        "shopping_list_entity",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not home_assistant.get(field)
    ]

    if missing_fields:
        raise ValueError(
            "Missing Home Assistant settings: "
            + ", ".join(missing_fields)
        )

    return home_assistant


def request_shopping_list(
    base_url,
    token,
    entity_id
):
    """
    Request the Alexa shopping list from Home Assistant.
    """
    url = (
        f"{base_url}"
        f"/api/services/todo/get_items"
        f"?return_response"
    )

    headers = {
        "Authorization": (
            f"Bearer {token}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "entity_id": entity_id,
        "status": "needs_action",
    }

    return requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=10
    )


def get_shopping_list():
    """
    Return active Alexa shopping-list items.

    If Home Assistant has just started and Alexa
    is still loading, retry for up to one minute.
    """
    settings = (
        get_home_assistant_settings()
    )

    base_url = (
        settings["url"].rstrip("/")
    )

    token = settings["token"]

    entity_id = (
        settings["shopping_list_entity"]
    )

    attempts = 12
    delay_seconds = 5

    for attempt in range(
        1,
        attempts + 1
    ):
        response = request_shopping_list(
            base_url,
            token,
            entity_id
        )

        if response.status_code == 200:
            data = response.json()

            service_response = data.get(
                "service_response",
                {}
            )

            entity_response = (
                service_response.get(
                    entity_id,
                    {}
                )
            )

            return entity_response.get(
                "items",
                []
            )

        if response.status_code in (
            500,
            502,
            503,
        ):
            if attempt < attempts:
                print(
                    "Alexa shopping list "
                    "not ready yet. "
                    f"Retrying in {delay_seconds} "
                    "seconds..."
                )

                time.sleep(
                    delay_seconds
                )

                continue

        response.raise_for_status()

    return []


def main():
    items = get_shopping_list()

    print()
    print("=" * 60)
    print("MARVIN - ALEXA SHOPPING LIST")
    print("=" * 60)

    if not items:
        print("Shopping list is empty.")
        return

    for item in items:
        print(
            "-",
            item.get(
                "summary",
                "(Unnamed item)"
            )
        )

    print()

    print(
        f"Total items: {len(items)}"
    )


if __name__ == "__main__":
    main()
