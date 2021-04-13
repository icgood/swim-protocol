
from __future__ import annotations

from abc import abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Optional, Protocol

from .config import Config
from .members import Member
from .types import Gossip, Handlers
from .util import load_plugin

__all__ = ['load_transport', 'Transport']


def load_transport(config: Config, name: Optional[str]) -> Transport:
    transport_cls = load_plugin(Transport, group=__name__, name=name)
    return transport_cls.init(config)


class Client(Protocol):

    @abstractmethod
    async def ping(self, member: Member) -> bool:
        ...

    @abstractmethod
    async def ping_req(self, member: Member, target: Member) -> bool:
        ...

    @abstractmethod
    async def sync(self, member: Member, gossip: Gossip) -> Optional[Gossip]:
        ...


class Transport(Protocol):

    @classmethod
    @abstractmethod
    def init(cls, config: Config) -> Transport:
        ...

    @property
    @abstractmethod
    def client(self) -> Client:
        ...

    @abstractmethod
    def enter(self, handlers: Handlers) -> AbstractAsyncContextManager[None]:
        ...
