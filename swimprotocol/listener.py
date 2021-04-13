
from __future__ import annotations

import asyncio
from asyncio import Event
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from typing import NoReturn
from weakref import WeakKeyDictionary

from .types import Update

__all__ = ['Listener']

_Callback = Callable[[Update], Awaitable[None]]


class Listener:

    def __init__(self) -> None:
        super().__init__()
        self.event = Event()
        self._updates: WeakKeyDictionary[Event, list[Update]] = \
            WeakKeyDictionary()

    async def _run_callback_poll(self, callback: _Callback) -> NoReturn:
        while True:
            updates = await self.poll()
            for update in updates:
                await callback(update)

    @asynccontextmanager
    async def on_update(self, callback: _Callback) -> AsyncIterator[None]:
        task = asyncio.create_task(self._run_callback_poll(callback))
        try:
            yield
        finally:
            task.cancel()

    async def poll(self) -> Sequence[Update]:
        event = Event()
        self._updates[event] = []
        await event.wait()
        return self._updates[event]

    def notify(self, update: Update) -> None:
        updates = self._updates
        for event in updates.keys():
            updates[event].append(update)
            event.set()
