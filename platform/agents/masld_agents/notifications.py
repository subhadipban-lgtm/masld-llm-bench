"""Pluggable notifications (log + optional macOS banner).

Notification delivery must never break an orchestration flow: every backend
swallows its own errors and reports success/failure out-of-band.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Protocol

logger = logging.getLogger("masld.agents")


class Notifier(Protocol):
    """A notification backend."""

    def send(self, title: str, message: str) -> bool: ...


class LogNotifier:
    """Always-on logging backend."""

    def send(self, title: str, message: str) -> bool:
        logger.info("[%s] %s", title, message)
        return True


class MacOSNotifier:
    """macOS banner notification via osascript; fails soft off-macOS."""

    def send(self, title: str, message: str) -> bool:
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "{title}"',
                ],
                check=True,
                timeout=10,
                capture_output=True,
            )
            return True
        except Exception as exc:  # noqa: BLE001 - never break the flow
            logger.debug("macos notification failed: %s", exc)
            return False


class CompositeNotifier:
    """Fan-out to several backends; returns True if any succeeded."""

    def __init__(self, *backends: Notifier) -> None:
        self.backends: list[Notifier] = list(backends) or [LogNotifier()]

    def send(self, title: str, message: str) -> bool:
        results = [b.send(title, message) for b in self.backends]
        return any(results)
