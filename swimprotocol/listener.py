
from __future__ import annotations

from abc import abstractmethod
from asyncio import Event
from collections.abc import Sequence
from typing import TypeVar, Generic, Protocol, Any, NoReturn
from weakref import WeakKeyDictionary

from .tasks import DaemonTask, TaskOwner

__all__ = ['ListenerCallback', 'CallbackPoll', 'Listener']

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


class CallbackPoll(Generic[ListenT], DaemonTask, TaskOwner):
    """Listens for items and running the callback.

    """

    def __init__(self, listener: Listener[ListenT],
                 callback: ListenerCallback[ListenT]) -> None:
        super().__init__()
        self._listener = listener
        self._callback = callback

    async def run(self) -> NoReturn:
        listener = self._listener
        callback = self._callback
        while True:
            items = await listener.poll()
            for item in items:
                self.run_subtask(callback(item))


class Listener(Generic[ListenT]):
    """Implements basic listener and callback functionality. Producers can
    call :meth:`.notify` with an item, and consumers can wait for those items
    with :meth:`.poll` or register a callback with :meth:`.on_notify`.

    """

    def __init__(self) -> None:
        super().__init__()
        self.event = Event()
        self._waiting: WeakKeyDictionary[Event, list[ListenT]] = \
            WeakKeyDictionary()

    def on_notify(self, callback: ListenerCallback[ListenT]) \
            -> CallbackPoll[ListenT]:
        """Provides a context manager that causes *callback* to be called when
        a producer calls :meth:`.notify`.

        Args:
            callback: The callback function, which will be passed the *item*
                argument from :meth:`.notify`.

        """
        return CallbackPoll(self, callback)

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
