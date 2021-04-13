
from __future__ import annotations

from typing import Final

from grpclib.server import Stream

from .adapter import proto_to_gossip, gossip_to_proto
from .proto.swimprotocol_pb2 import SwimPing, SwimPingReq, SwimAck, SwimGossip
from .proto.swimprotocol_grpc import SwimProtocolBase
from ..types import Handlers

__all__ = ['SwimServer']


class SwimServer(SwimProtocolBase):

    def __init__(self, handlers: Handlers) -> None:
        super().__init__()
        self.handlers: Final = handlers

    async def Ping(self, stream: Stream[SwimPing, SwimAck]) -> None:
        request = await stream.recv_message()
        assert request is not None
        online = await self.handlers.handle_ping()
        await stream.send_message(SwimAck(online=online))

    async def PingReq(self, stream: Stream[SwimPingReq, SwimAck]) -> None:
        request = await stream.recv_message()
        assert request is not None
        online = await self.handlers.handle_ping_req(request.target)
        await stream.send_message(SwimAck(online=online))

    async def Sync(self, stream: Stream[SwimGossip, SwimGossip]) -> None:
        request = proto_to_gossip(await stream.recv_message())
        gossip = await self.handlers.handle_sync(request)
        await stream.send_message(gossip_to_proto(gossip))
