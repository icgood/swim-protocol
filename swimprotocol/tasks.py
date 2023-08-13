
from __future__ import annotations

import asyncio
from abc import abstractmethod, ABCMeta
from asyncio import Task
from collections.abc import Coroutine, MutableSet
from contextlib import AbstractAsyncContextManager
from typing import Any, NoReturn, Optional, TypeVar

__all__ = ['TaskT', 'DaemonTask', 'TaskOwner']

#: The type of task result.
TaskT = TypeVar('TaskT')


class TaskOwner:
    """Base class for any class that needs to run sub-tasks.

    Because :mod:`asyncio` can be garbage-collected while running, the purpose
    of this base class is to keep a strong reference to all running tasks. The
    task removes its own reference when it is complete, effectively allowing it
    to "daemonize".

    """

    def __init__(self) -> None:
        super().__init__()
        self._running: MutableSet[Task[Any]] = set()

    def run_subtask(self, coro: Coroutine[Any, Any, TaskT]) -> Task[TaskT]:
        """Run the *coro* sub-task.

        Args:
            coro: The coroutine to run.

        """
        running = self._running
        task = asyncio.create_task(coro)
        running.add(task)
        task.add_done_callback(running.discard)
        return task


class DaemonTask(AbstractAsyncContextManager[Task[NoReturn]],
                 metaclass=ABCMeta):
    """Base class for a task that is run for the duration of an ``async with``
    context.

    """

    def __init__(self) -> None:
        super().__init__()
        self._task: Optional[Task[NoReturn]] = None

    async def __aenter__(self) -> Task[TaskT]:
        self._task = task = asyncio.create_task(self.run())
        return task

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) \
            -> Any:
        task = self._task
        if task is not None:
            task.cancel()

    @abstractmethod
    async def run(self) -> NoReturn:
        """The method to run while the context is entered. The task is
        cancelled when the context exits.

        """
        ...
