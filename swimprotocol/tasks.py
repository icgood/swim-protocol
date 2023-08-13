
from __future__ import annotations

import asyncio
from asyncio import Task
from collections.abc import Coroutine, MutableSet
from typing import Any

__all__ = ['Subtasks']


class Subtasks:
    """Base class for any class that needs to run sub-tasks."""

    def __init__(self) -> None:
        super().__init__()
        self._running: MutableSet[Task[Any]] = set()

    def run_subtask(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Run the *coro* sub-task.

        Args:
            coro: The coroutine to run.

        """
        running = self._running
        task = asyncio.create_task(coro)
        running.add(task)
        task.add_done_callback(running.discard)
