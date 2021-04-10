
from __future__ import annotations

import asyncio
from asyncio import wait_for, Future
from collections.abc import Iterable
from typing import Final, Optional

from grpclib.server import Stream

from .config import Config
from .grpc.swimprotocol_pb2 import Ping, PingReq, Ack, Failure, Status, Gossip
from .grpc.swimprotocol_grpc import SwimProtocolBase, SwimProtocolStub
from .members import Member, Members

__all__ = ['SwimServer']


class SwimServer(SwimProtocolBase):

    def __init__(self, config: Config, members: Members) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members

    async def PingCommand(self, stream: Stream[Ping, Ack]) -> None:
        request = await stream.recv_message()
        assert request is not None
        await stream.send_message(Ack())

    async def PingReqCommand(self, stream: Stream[PingReq, Ack]) -> None:
        request = await stream.recv_message()
        assert request is not None
        member = self.members.get(request.target)
        await stream.send_message(await self._ping(member))

    async def SyncCommand(self, stream: Stream[Gossip, Gossip]) -> None:
        request = await stream.recv_message()
        assert request is not None
        source = self.members.apply(request)
        gossip = self.members.get_gossip(source)
        await stream.send_message(gossip)

    async def _ping(self, member: Member) -> Ack:
        async with member.get_channel() as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await wait_for(
                    self._ping_cmd(stub, member),
                    timeout=self.config.ping_timeout)
            except Exception as exc:
                failure = Failure(key=str(type(exc)), msg=str(exc))
                return Ack(failure=failure)

    async def _ping_req(self, member: Member, target: Member) -> Optional[Ack]:
        async with member.get_channel() as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await wait_for(
                    self._ping_req_cmd(stub, member, target),
                    timeout=self.config.ping_req_timeout)
            except Exception:
                return None

    async def _ping_cmd(self, stub: SwimProtocolStub,
                        recipient: Member) -> Ack:
        return await stub.PingCommand(Ping())

    async def _ping_req_cmd(self, stub: SwimProtocolStub,
                            recipient: Member, target: Member) -> Ack:
        return await stub.PingReqCommand(
            PingReq(target=str(target.address)))

    async def _run_failure_detection(self) -> None:
        while True:
            await asyncio.sleep(self.config.ping_period)
            target = self.members.get_target()
            ack = await self._ping(target)
            if ack.HasField('failure'):
                indirects = self.members.get_indirect(target)
                if indirects:
                    ping_reqs = (self._ping_req(indirect, target)
                                 for indirect in indirects)
                    acks: list[Optional[Ack]] = \
                        await asyncio.gather(*ping_reqs)
                    success = self._find_success(acks)
                    if success is not None:
                        ack = success
            status = Status.DOWN if ack.HasField('failure') else Status.UP
            target.set_status(status)

    def _find_success(self, acks: Iterable[Optional[Ack]]) -> Optional[Ack]:
        for ack in acks:
            if ack is not None:
                if not ack.HasField('failure'):
                    return ack
        return None

    async def _sync(self, member: Member, gossip: Gossip) -> Optional[Gossip]:
        async with member.get_channel() as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await wait_for(
                    self._sync_cmd(stub, gossip),
                    timeout=self.config.sync_timeout)
            except Exception:
                pass
        return None

    async def _sync_cmd(self, stub: SwimProtocolStub,
                        gossip: Gossip) -> Gossip:
        return await stub.SyncCommand(gossip)

    async def _run_dissemination(self) -> None:
        while True:
            await asyncio.sleep(self.config.sync_period)
            target = self.members.get_target()
            my_gossip = self.members.get_gossip(target)
            their_gossip = await self._sync(target, my_gossip)
            if their_gossip is not None:
                self.members.apply(their_gossip)

    def start(self) -> Future[tuple[None, None]]:
        return asyncio.gather(
            self._run_failure_detection(),
            self._run_dissemination())
