
from __future__ import annotations

import asyncio
from asyncio import wait_for, Future, Event
from collections.abc import Iterable, AsyncIterable
from typing import Final, Optional

from grpclib.server import Stream

from .config import Config
from .grpc.swimprotocol_pb2 import Ping, PingReq, Ack, Failure, \
    Update, Gossip
from .grpc.swimprotocol_grpc import SwimProtocolBase, SwimProtocolStub
from .members import Member, Members

__all__ = ['SwimServer']


class SwimServer(SwimProtocolBase):

    def __init__(self, config: Config, members: Members) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members
        self.introduced: Final = Event()

    async def PingCommand(self, stream: Stream[Ping, Ack]) -> None:
        request = await stream.recv_message()
        assert request is not None
        await self.introduced.wait()
        await stream.send_message(Ack())

    async def PingReqCommand(self, stream: Stream[PingReq, Ack]) -> None:
        request = await stream.recv_message()
        assert request is not None
        await self.introduced.wait()
        member = self.members.get(request.target)
        await stream.send_message(await self._ping(member))

    async def IntroduceCommand(self, stream: Stream[Update, Gossip]) -> None:
        request = await stream.recv_message()
        assert request is not None
        gossip = self.members.introduce(request)
        await stream.send_message(gossip)

    async def SyncCommand(self, stream: Stream[Gossip, Gossip]) -> None:
        request = await stream.recv_message()
        assert request is not None
        await self.introduced.wait()
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
            online = not ack.HasField('failure')
            target.set_status(online)

    def _find_success(self, acks: Iterable[Optional[Ack]]) -> Optional[Ack]:
        for ack in acks:
            if ack is not None:
                if not ack.HasField('failure'):
                    return ack
        return None

    async def _introduce(self, member: Member, update: Update) \
            -> Optional[Gossip]:
        async with member.get_channel() as channel:
            stub = SwimProtocolStub(channel)
            try:
                return await wait_for(
                    self._introduce_cmd(stub, update),
                    timeout=self.config.introduce_timeout)
            except Exception:
                pass
        return None

    async def _introduce_cmd(self, stub: SwimProtocolStub,
                             update: Update) -> Gossip:
        return await stub.IntroduceCommand(update)

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

    async def _run_introductions(self) -> AsyncIterable[Gossip]:
        local_update = self.members.local.update
        introduced = self.introduced
        while not introduced.is_set():
            pending_intros: set[Future[Optional[Gossip]]] = {
                asyncio.create_task(self._introduce(target, local_update))
                for target in self.members.non_local}
            while pending_intros:
                done, pending_intros = await asyncio.wait(
                    pending_intros, return_when=asyncio.FIRST_COMPLETED)
                for fut in done:
                    intro_gossip = await fut
                    if intro_gossip is not None:
                        yield intro_gossip
                        introduced.set()
            if not introduced.is_set():
                await asyncio.sleep(self.config.introduce_period)

    async def _run_dissemination(self) -> None:
        async for intro_gossip in self._run_introductions():
            self.members.apply(intro_gossip)
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
