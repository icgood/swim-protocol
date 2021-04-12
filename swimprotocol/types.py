
from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence, Mapping
from dataclasses import dataclass
from enum import auto, Flag
from typing import Protocol

__all__ = ['Address', 'Status', 'Update', 'Gossip']


@dataclass(frozen=True)
class Address:
    host: str
    port: int

    def __str__(self) -> str:
        return ':'.join((self.host, str(self.port)))

    @classmethod
    def parse(cls, address: str) -> Address:
        host, sep, port = address.rpartition(':')
        if sep != ':' or not host:
            raise ValueError()
        return cls(host, int(port))


class Status(Flag):
    OFFLINE = auto()
    ONLINE = auto()
    SUSPECT = OFFLINE | ONLINE


@dataclass(frozen=True)
class Update:
    address: Address
    clock: int
    status: Status
    metadata: Mapping[str, str]

    @property
    def address_str(self) -> str:
        return str(self.address)


@dataclass(frozen=True)
class Gossip:
    source: Address
    updates: Sequence[Update]

    @property
    def source_str(self) -> str:
        return str(self.source)


class Handlers(Protocol):

    @abstractmethod
    async def handle_ping(self) -> bool:
        ...

    @abstractmethod
    async def handle_ping_req(self, target: str) -> bool:
        ...

    @abstractmethod
    async def handle_introduce(self, update: Update) -> Gossip:
        ...

    @abstractmethod
    async def handle_sync(self, gossip: Gossip) -> Gossip:
        ...
