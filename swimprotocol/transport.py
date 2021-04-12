
from __future__ import annotations

from abc import abstractmethod, ABCMeta
from argparse import Namespace
from contextlib import AbstractAsyncContextManager
from typing import Final, Optional, Protocol

from pkg_resources import iter_entry_points, EntryPoint

from .config import Config
from .members import Member
from .types import Update, Gossip, Handlers

__all__ = ['load_transport', 'Transport']


def load_transport(args: Namespace, *, group: str = __name__) -> Transport:
    name: Optional[str] = args.transport
    selected_entry_point: Optional[EntryPoint] = None
    for entry_point in iter_entry_points(group, name):
        selected_entry_point = entry_point
    assert selected_entry_point is not None, \
        f'{group!r} entry point has no matching implementations'
    load_cls: type[Transport] = selected_entry_point.load()
    assert issubclass(load_cls, Transport), \
        f'{selected_entry_point.name!r} is not a {Transport!r}'
    return load_cls(args)


class Client(Protocol):

    @abstractmethod
    async def ping(self, member: Member) -> bool:
        ...

    @abstractmethod
    async def ping_req(self, member: Member, target: Member) -> bool:
        ...

    @abstractmethod
    async def introduce(self, member: Member, update: Update) \
            -> Optional[Gossip]:
        ...

    @abstractmethod
    async def sync(self, member: Member, gossip: Gossip) -> Optional[Gossip]:
        ...


class Transport(metaclass=ABCMeta):

    def __init__(self, args: Namespace) -> None:
        super().__init__()
        self.args: Final = args

    @property
    @abstractmethod
    def config(self) -> Config:
        ...

    @property
    @abstractmethod
    def client(self) -> Client:
        ...

    @abstractmethod
    def enter(self, handlers: Handlers) -> AbstractAsyncContextManager[None]:
        ...
