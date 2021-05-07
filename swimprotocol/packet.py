
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

from .status import Status

__all__ = ['Packet', 'Ping', 'PingReq', 'Ack', 'Gossip', 'GossipAck']


@dataclass(frozen=True)
class Packet:
    """Base class for a :term:`packet` sent between cluster members.

    :class:`~swimprotocol.transport.Transport` implementations may use these
    directly, e.g. :class:`~swimprotocol.udp.pack.UdpPack`, or adapt their
    contents into another protocol.

    Args:
        source: The name of the local cluster member that created the packet.

    """

    source: tuple[str, bytes]


@dataclass(frozen=True)
class Ping(Packet):
    """Packets used for the SWIM protocol :term:`ping` operation, which do not
    explicitly contain any other information other than the *source*.

    """
    pass


@dataclass(frozen=True)
class PingReq(Packet):
    """Packets used for the SWIM protocol :term:`ping-req` operation, which
    contain a *target* member in addition to *source*.

    Args:
        target: The name of the target cluster member.

    """

    target: str


@dataclass(frozen=True)
class Ack(Packet):
    """Packets used for the SWIM protocol :term:`ack` response, which indicates
    that *source* is online.

    """

    pass


@dataclass(frozen=True)
class Gossip(Packet):
    """Packets used for SWIM protocol :term:`gossip`, which alert other members
    when a cluster member has changed status or metadata. This information is
    intended to travel around the cluster until all members are aware of the
    change.

    Args:
        name: The name of the cluster member whose state has changed.
        clock: The sequence clock value associated with the change.
        status: The current perceived status of the cluster member.
        metadata: The current metadata associated with the cluster member.

    """

    name: str
    clock: int
    status: Status
    metadata: Optional[Mapping[str, bytes]]


@dataclass(frozen=True)
class GossipAck(Packet):
    """Packets used to acknowledge receipt of a :class:`Gossip` packet.

    Args:
        name: The name of the cluster member from the :class:`Gossip` packet.
        clock: The sequence clock from the :class:`Gossip` packet.

    """

    name: str
    clock: int
