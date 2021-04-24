
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
    """A callback that is called given the *update* item on
    :meth:`~Listener.notify`.

    """

    @abstractmethod
    async def __call__(self, updated: ListenT_contra) -> None:
        ...


class Listener(Generic[ListenT]):
    """Implements basic listener and callback functionality. Producers can
    call :meth:`.notify` with an updated item, and consumers can wait for those
    items with :meth:`.poll` or register a callback with :meth:`.on_update`.

    Args:
        cls: The item type that will be given to :meth:`.notify`, returned by
            :meth:`.poll`, and passed to :meth:`.on_update` callbacks.

    """

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
        """Provides a context manager that when entered ensures *callback* is
        called when a producer calls :meth:`.notify`.

        Args:
            callback: The callback function, which will be passed the *update*
                item when notifications occur.

        """
        exit_stack = ExitStack()
        task = asyncio.create_task(self._run_callback_poll(callback))
        exit_stack.callback(task.cancel)
        return exit_stack

    async def poll(self) -> Sequence[ListenT]:
        """Wait until :meth:`.notify` is called and return all *update* items.
        More than one item may be returned if :meth:`.notify` is called more
        than once before the :mod:`asyncio` event loop is re-entered.

        """
        event = Event()
        self._updates[event] = []
        await event.wait()
        return self._updates[event]

    def notify(self, update: ListenT) -> None:
        """Triggers a notification on the *update* item, waking any
        :meth:`.poll` calls and running any :meth:`.on_update` callbacks.

        Args:
            update: The item to be sent to the consumers.

        """
        updates = self._updates
        for event in updates.keys():
            updates[event].append(update)
            event.set()
