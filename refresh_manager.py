from __future__ import annotations

import threading
import time

from datetime import datetime


FAILURE_LIMIT = 5


class RefreshManager:
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()

    def register(
        self,
        name,
        interval,
        function,
    ):
        self.tasks[name] = {
            "interval": int(interval),
            "function": function,
            "last_result": None,
            "last_attempt": None,
            "last_success": None,
            "consecutive_failures": 0,
            "last_error": None,
            "thread": None,
        }

    def _run_task(self, name):
        task = self.tasks[name]

        with self.lock:
            task["last_attempt"] = datetime.now()

        try:
            result = task["function"]()

            with self.lock:
                task["last_result"] = result
                task["last_success"] = datetime.now()
                task["consecutive_failures"] = 0
                task["last_error"] = None

            print(
                f"[{datetime.now().strftime('%I:%M:%S %p')}] "
                f"{name} updated"
            )

            return True

        except Exception as error:
            with self.lock:
                task["consecutive_failures"] += 1
                task["last_error"] = str(error)

                failures = task[
                    "consecutive_failures"
                ]

            print(
                f"[{datetime.now().strftime('%I:%M:%S %p')}] "
                f"{name} refresh failed "
                f"({failures}/{FAILURE_LIMIT}): "
                f"{error}"
            )

            return False

    def run_once(self, name):
        return self._run_task(name)

    def run_all_once(self):
        for name in self.tasks:
            self._run_task(name)

    def _worker(self, name):
        task = self.tasks[name]
        interval = task["interval"]

        while True:
            time.sleep(interval)
            self._run_task(name)

    def start(self):
        print()
        print("=" * 60)
        print("MARVIN REFRESH SYSTEM")
        print("=" * 60)

        for name, task in self.tasks.items():
            print(
                f"{name:<18} every "
                f"{task['interval']} seconds"
            )

        print("=" * 60)

        self.run_all_once()

        for name, task in self.tasks.items():
            thread = threading.Thread(
                target=self._worker,
                args=(name,),
                daemon=True,
                name=f"marvin-refresh-{name}",
            )

            task["thread"] = thread
            thread.start()

    def get_result(self, name, default=None):
        task = self.tasks.get(name)

        if task is None:
            return default

        with self.lock:
            result = task["last_result"]

        if result is None:
            return default

        return result

    def get_status(self, name):
        task = self.tasks.get(name)

        if task is None:
            return {
                "registered": False,
                "problem": False,
                "failures": 0,
                "last_success": None,
                "last_attempt": None,
                "last_error": None,
            }

        with self.lock:
            failures = task[
                "consecutive_failures"
            ]

            last_success = task[
                "last_success"
            ]

            last_attempt = task[
                "last_attempt"
            ]

            last_error = task[
                "last_error"
            ]

        return {
            "registered": True,
            "problem": failures >= FAILURE_LIMIT,
            "failures": failures,
            "last_success": (
                last_success.strftime(
                    "%I:%M %p"
                ).lstrip("0")
                if last_success
                else None
            ),
            "last_attempt": (
                last_attempt.strftime(
                    "%I:%M %p"
                ).lstrip("0")
                if last_attempt
                else None
            ),
            "last_error": last_error,
        }


refresh_manager = RefreshManager()
