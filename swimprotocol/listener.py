
from __future__ import annotations

import asyncio
from abc import abstractmethod
from asyncio import Event
from collections.abc import Sequence
from contextlib import ExitStack
from typing import TypeVar, Generic, Protocol, Any, NoReturn
from weakref import WeakKeyDictionary

__all__ = ['ListenerCallback', 'Listener']

ListenT = TypeVar('ListenT')
ListenT_contra = TypeVar('ListenT_contra', contravariant=True)


class ListenerCallback(Protocol[ListenT_contra]):

    @abstractmethod
    async def __call__(self, item: ListenT_contra, /) -> Any:
        """Called asynchronousely with the argument passed to
        :meth:`~Listener.notify`.

        Args:
            item: The object sent to the consumers.

        """
        ...


class Listener(Generic[ListenT]):
    """Implements basic listener and callback functionality. Producers can
    call :meth:`.notify` with an item, and consumers can wait for those items
    with :meth:`.poll` or register a callback with :meth:`.on_notify`.

    Args:
        cls: The item type that will be given to :meth:`.notify`, returned by
            :meth:`.poll`, and passed to :meth:`.on_notify` callbacks.

    """

    def __init__(self, cls: type[ListenT]) -> None:
        super().__init__()
        self.event = Event()
        self._waiting: WeakKeyDictionary[Event, list[ListenT]] = \
            WeakKeyDictionary()

    async def _run_callback_poll(self, callback: ListenerCallback[ListenT]) \
            -> NoReturn:
        while True:
            items = await self.poll()
            for item in items:
                asyncio.create_task(callback(item))

    def on_notify(self, callback: ListenerCallback[ListenT]) -> ExitStack:
        """Provides a context manager that causes *callback* to be called when
        a producer calls :meth:`.notify`.

        Args:
            callback: The callback function, which will be passed the *item*
                argument from :meth:`.notify`.

        """
        exit_stack = ExitStack()
        task = asyncio.create_task(self._run_callback_poll(callback))
        exit_stack.callback(task.cancel)
        return exit_stack

    async def poll(self) -> Sequence[ListenT]:
        """Wait until :meth:`.notify` is called and return all *item* objects.
        More than one item may be returned if :meth:`.notify` is called more
        than once before the :mod:`asyncio` event loop is re-entered.

        """
        event = Event()
        self._waiting[event] = []
        await event.wait()
        return self._waiting[event]

    def notify(self, item: ListenT) -> None:
        """Triggers a notification with *item*, waking any :meth:`.poll` calls
        and running any :meth:`.on_notify` callbacks.

        Args:
            item: The object to be sent to the consumers.

        """
        for event, args in self._waiting.items():
            args.append(item)
            event.set()
