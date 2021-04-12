
from __future__ import annotations

import asyncio
from asyncio import CancelledError, Future
from collections.abc import Awaitable, Iterable, AsyncIterable
from typing import TypeVar

__all__ = ['as_available']

T1 = TypeVar('T1')


async def as_available(pending: Iterable[Awaitable[T1]]) -> AsyncIterable[T1]:
    pending_tasks: set[Future[T1]] = {
        asyncio.create_task(fut) for fut in pending}
    while pending_tasks:
        done, pending_tasks = await asyncio.wait(
            pending_tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            result = await task
            try:
                yield result
            except CancelledError:
                for task in pending_tasks:
                    task.cancel()
                raise
