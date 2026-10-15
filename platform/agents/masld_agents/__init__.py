"""Supervisory agents: task execution registry, control loop, notifications."""

from masld_agents.notifications import CompositeNotifier, LogNotifier, MacOSNotifier
from masld_agents.tasks import RunOutcome, execute_spec

__all__ = [
    "CompositeNotifier",
    "LogNotifier",
    "MacOSNotifier",
    "RunOutcome",
    "execute_spec",
]
