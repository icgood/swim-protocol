
from __future__ import annotations

import asyncio
from abc import abstractmethod
from asyncio import Event
from collections.abc import Sequence
from contextlib import ExitStack
from typing import TypeVar, Generic, Protocol, NoReturn
from weakref import WeakKeyDictionary

__all__ = ['Listener']

ListenT = TypeVar('ListenT')
ListenT_contra = TypeVar('ListenT_contra', contravariant=True)


class ListenerCallback(Protocol[ListenT_contra]):

    @abstractmethod
    async def __call__(self, updated: ListenT_contra) -> None:
        ...


class Listener(Generic[ListenT]):

    def __init__(self, cls: type[ListenT]) -> None:
        super().__init__()
        self.event = Event()
        self._updates: WeakKeyDictionary[Event, list[ListenT]] = \
            WeakKeyDictionary()

    async def _run_callback_poll(self, callback: ListenerCallback[ListenT]) \
            -> NoReturn:
        while True:
            updates = await self.poll()
            for update in updates:
                await callback(update)

    def on_update(self, callback: ListenerCallback[ListenT]) -> ExitStack:
        exit_stack = ExitStack()
        task = asyncio.create_task(self._run_callback_poll(callback))
        exit_stack.callback(task.cancel)
        return exit_stack

    async def poll(self) -> Sequence[ListenT]:
        event = Event()
        self._updates[event] = []
        await event.wait()
        return self._updates[event]

    def notify(self, update: ListenT) -> None:
        updates = self._updates
        for event in updates.keys():
            updates[event].append(update)
            event.set()
