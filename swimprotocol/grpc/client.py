
from __future__ import annotations

import asyncio
from typing import Final, Optional
from weakref import WeakKeyDictionary

from grpclib.client import Channel

from .adapter import gossip_to_proto, proto_to_gossip
from .proto.swimprotocol_grpc import SwimProtocolStub
from .proto.swimprotocol_pb2 import SwimPing, SwimPingReq
from ..config import Config
from ..members import Member
from ..transport import Client
from ..types import Gossip

__all__ = ['GrpcClient']


class GrpcClient(Client):

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config: Final = config
        self._channels: WeakKeyDictionary[Member, Channel] = \
            WeakKeyDictionary()

    def get_channel(self, member: Member) -> Channel:
        channel = self._channels.get(member)
        if channel is None:
            self._channels[member] = channel = Channel(
                member.address.host, member.address.port,
                ssl=self.config.ssl_context)
        return channel

    async def _ping_call(self, stub: SwimProtocolStub,
                         recipient: Member) -> bool:
        ack = await stub.Ping(SwimPing())
        return ack.online

    async def ping(self, member: Member) -> bool:
        async with self.get_channel(member) as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await asyncio.wait_for(
                    self._ping_call(stub, member),
                    timeout=self.config.ping_timeout)
            except Exception:
                return False

    async def _ping_req_call(self, stub: SwimProtocolStub,
                             recipient: Member, target: Member) -> bool:
        ack = await stub.PingReq(
            SwimPingReq(target=str(target.address)))
        return ack.online

    async def ping_req(self, member: Member, target: Member) -> bool:
        async with self.get_channel(member) as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await asyncio.wait_for(
                    self._ping_req_call(stub, member, target),
                    timeout=self.config.ping_req_timeout)
            except Exception:
                return False

    async def _sync_call(self, stub: SwimProtocolStub,
                         gossip: Gossip) -> Gossip:
        gossip_proto = gossip_to_proto(gossip)
        return proto_to_gossip(await stub.Sync(gossip_proto))

    async def sync(self, member: Member, gossip: Gossip) -> Optional[Gossip]:
        async with self.get_channel(member) as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await asyncio.wait_for(
                    self._sync_call(stub, gossip),
                    timeout=self.config.sync_timeout)
            except Exception:
                pass
        return None
