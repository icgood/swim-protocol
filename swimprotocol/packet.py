
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

from .status import Status

__all__ = ['Packet', 'Ping', 'PingReq', 'Ack', 'Gossip']


@dataclass(frozen=True)
class Packet:
    """Base class for "packets" sent between cluster members.

    :class:`~swimprotocol.transport.Transport` implementations may use these
    directly, e.g. :class:`~swimprotocol.udp.UdpPack`, or adapt their contents
    into another protocol.

    Args:
        source: The name of the local cluster member that created the packet.

    """

    source: str


@dataclass(frozen=True)
class Ping(Packet):
    """Packets used for the SWIM protocol *ping* operation, which do not
    explicitly contain any other information other than the *source*. The
    *ping* operation simply asks the destination member to send it an *ack*
    response.

    """
    pass


@dataclass(frozen=True)
class PingReq(Packet):
    """Packets used for the SWIM protocol *ping-req* operation, which contain
    a *target* member in addition to *source*. The *ping-req* operation asks
    another member to *ping* the target, and forward any received *ack*
    responses back to the source.

    Args:
        target: The name of the target cluster member.

    """

    target: str


@dataclass(frozen=True)
class Ack(Packet):
    """Packets used for the SWIM protocol *ack* response, which indicates that
    *source* is online.

    """

    pass


@dataclass(frozen=True)
class Gossip(Packet):
    """Packets used for SWIM protocol dissemination, which alert other members
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
    metadata: Optional[Mapping[bytes, bytes]]
