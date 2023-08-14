
from __future__ import annotations

from asyncio import Event
from collections.abc import Sequence
from typing import Callable, TypeAlias, TypeVar, Generic, Any, NoReturn
from typing_extensions import Concatenate, ParamSpec
from weakref import WeakKeyDictionary

from .tasks import DaemonTask, TaskOwner

__all__ = ['ListenerCallback', 'CallbackPoll', 'Listener']

ListenT = TypeVar('ListenT')
ListenT_contra = TypeVar('ListenT_contra', contravariant=True)
ListenP = ParamSpec('ListenP')

#: A callable that takes the notified item.
ListenerCallback: TypeAlias = Callable[
    Concatenate[ListenT_contra, ListenP],
    Any]


class CallbackPoll(Generic[ListenT, ListenP], DaemonTask, TaskOwner):
    """Listens for items and running the callback.

    """

    def __init__(self, listener: Listener[ListenT],
                 callback: ListenerCallback[ListenT, ListenP],
                 *args: ListenP.args, **kwargs: ListenP.kwargs) -> None:
        super().__init__()
        self._listener = listener
        self._callback = callback
        self._args = args
        self._kwargs = kwargs

    async def run(self) -> NoReturn:
        listener = self._listener
        callback = self._callback
        args = self._args
        kwargs = self._kwargs
        while True:
            items = await listener.poll()
            for item in items:
                self.run_subtask(callback(item, *args, **kwargs))


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

    def on_notify(self, callback: ListenerCallback[ListenT, ListenP],
                  *args: ListenP.args, **kwargs: ListenP.kwargs) \
            -> CallbackPoll[ListenT, ListenP]:
        """Provides a context manager that causes *callback* to be called when
        a producer calls :meth:`.notify`.

        Args:
            callback: The callback function, which will be passed the *item*
                argument from :meth:`.notify`.

        """
        return CallbackPoll(self, callback, *args, **kwargs)

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
