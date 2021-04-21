
from __future__ import annotations

from abc import ABCMeta
from collections.abc import Mapping
from dataclasses import dataclass
from enum import auto, Flag
from typing import Optional

__all__ = ['Status', 'Packet', 'Ping', 'PingReq', 'Ack', 'Gossip']


class Status(Flag):
    ONLINE = auto()
    OFFLINE = auto()
    BAD_SIG = auto()

    # Aggregates
    AVAILABLE = ONLINE
    UNAVAILABLE = OFFLINE | BAD_SIG


@dataclass(frozen=True)
class Packet(metaclass=ABCMeta):
    source: str


@dataclass(frozen=True)
class Ping(Packet):
    pass


@dataclass(frozen=True)
class PingReq(Packet):
    target: str


@dataclass(frozen=True)
class Ack(Packet):
    pass


@dataclass(frozen=True)
class Gossip(Packet):
    name: str
    clock: int
    status: Status
    metadata: Optional[Mapping[str, str]]
