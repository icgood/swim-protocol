
from __future__ import annotations

from typing import Optional

from .proto.swimprotocol_pb2 import SwimStatus, SwimUpdate, SwimGossip
from ..types import Address, Status, Update, Gossip

__all__ = ['status_to_proto', 'proto_to_status',
           'update_to_proto', 'proto_to_update',
           'gossip_to_proto', 'proto_to_gossip']


def status_to_proto(status: Status) -> SwimStatus.V:
    if status == Status.OFFLINE:
        return SwimStatus.OFFLINE
    elif status == Status.ONLINE:
        return SwimStatus.ONLINE
    else:
        raise ValueError(status)


def proto_to_status(status: SwimStatus.V) -> Status:
    if status == SwimStatus.OFFLINE:
        return Status.OFFLINE
    elif status == SwimStatus.ONLINE:
        return Status.ONLINE
    else:
        raise ValueError(status)


def update_to_proto(update: Optional[Update]) -> SwimUpdate:
    assert update is not None
    proto = SwimUpdate(address=str(update.address),
                       status=status_to_proto(update.status),
                       metadata=update.metadata)
    if update.modified is not None:
        proto.MergeFrom(SwimUpdate(modified=update.modified))
    return proto


def proto_to_update(update: Optional[SwimUpdate]) -> Update:
    assert update is not None
    modified = update.modified if update.HasField('modified') else None
    return Update(address=Address.parse(update.address),
                  modified=modified,
                  status=proto_to_status(update.status),
                  metadata=update.metadata)


def gossip_to_proto(gossip: Optional[Gossip]) -> SwimGossip:
    assert gossip is not None
    return SwimGossip(source=str(gossip.source),
                      clock=gossip.clock,
                      updates=[update_to_proto(update)
                               for update in gossip.updates])


def proto_to_gossip(gossip: Optional[SwimGossip]) -> Gossip:
    assert gossip is not None
    return Gossip(source=Address.parse(gossip.source),
                  clock=gossip.clock,
                  updates=[proto_to_update(update)
                           for update in gossip.updates])
