
from __future__ import annotations

import asyncio
from asyncio import CancelledError, Future
from collections.abc import Awaitable, Iterable, AsyncIterable
from typing import TypeVar, Optional

from pkg_resources import iter_entry_points, EntryPoint

__all__ = ['load_plugin', 'as_available']

T1 = TypeVar('T1')
TypeT = TypeVar('TypeT', bound='type')


def load_plugin(base: TypeT, *, group: str,
                name: Optional[str] = None) -> TypeT:
    selected_entry_point: Optional[EntryPoint] = None
    for entry_point in iter_entry_points(group, name):
        selected_entry_point = entry_point
    assert selected_entry_point is not None, \
        f'{group!r} entry point has no matching implementations'
    return selected_entry_point.load()


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
