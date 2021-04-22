
from __future__ import annotations

import asyncio
import time
from abc import abstractmethod
from asyncio import Event, TimeoutError
from collections.abc import Sequence
from contextlib import suppress
from typing import Protocol, Final, NoReturn
from weakref import WeakSet, WeakKeyDictionary

from .config import Config
from .members import Member, Members
from .packet import Status, Packet, Ping, PingReq, Ack, Gossip

__all__ = ['Worker']


class IO(Protocol):

    @abstractmethod
    async def recv(self) -> Packet:
        ...

    @abstractmethod
    async def send(self, member: Member, packet: Packet) -> None:
        ...


class Worker:

    def __init__(self, config: Config, members: Members, io: IO) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members
        self.io: Final = io
        self._waiting: WeakKeyDictionary[Member, WeakSet[Event]] = \
            WeakKeyDictionary()
        self._listening: WeakKeyDictionary[Member, WeakSet[Member]] = \
            WeakKeyDictionary()

    def _add_waiting(self, member: Member, event: Event) -> None:
        waiting = self._waiting.get(member)
        if waiting is None:
            self._waiting[member] = waiting = WeakSet()
        waiting.add(event)

    def _add_listening(self, member: Member, target: Member) -> None:
        listening = self._listening.get(target)
        if listening is None:
            self._listening[target] = listening = WeakSet()
        listening.add(member)

    def _notify_waiting(self, member: Member) -> None:
        waiting = self._waiting.get(member)
        if waiting is not None:
            for event in waiting:
                event.set()

    def _get_listening(self, member: Member) -> Sequence[Member]:
        listening = self._listening.pop(member, None)
        if listening is not None:
            return list(listening)
        else:
            return []

    async def _run_handler(self) -> None:
        local = self.members.local
        while True:
            packet = await self.io.recv()
            source = self.members.get(packet.source)
            if isinstance(packet, Ping):
                await self.io.send(source, Ack(source=local.name))
            elif isinstance(packet, PingReq):
                target = self.members.get(packet.target)
                await self.io.send(target, Ping(source=local.name))
                self._add_listening(source, target)
            elif isinstance(packet, Ack):
                self._notify_waiting(source)
                for target in self._get_listening(source):
                    await self.io.send(target, packet)
            elif isinstance(packet, Gossip):
                self.members.apply_gossip(packet)

    async def _wait(self, target: Member, timeout: float) -> bool:
        event = Event()
        self._add_waiting(target, event)
        with suppress(TimeoutError):
            await asyncio.wait_for(event.wait(), timeout)
        return event.is_set()

    async def _check(self, target: Member) -> None:
        local = self.members.local
        await self.io.send(target, Ping(source=local.name))
        online = await self._wait(target, self.config.ping_timeout)
        if not online:
            indirects = self.members.get_indirect(target)
            if indirects:
                await asyncio.wait([
                    self.io.send(indirect, PingReq(
                        source=local.name, target=target.name))
                    for indirect in indirects])
                online = await self._wait(target, self.config.ping_req_timeout)
        new_status = Status.ONLINE if online else Status.SUSPECT
        self.members.notify(target, new_status=new_status)

    async def _disseminate(self, target: Member) -> None:
        for gossip in self.members.get_gossip(target):
            await self.io.send(target, gossip)

    async def _run_failure_detection(self) -> None:
        while True:
            target = self.members.get_target()
            asyncio.create_task(self._check(target))
            await asyncio.sleep(self.config.ping_period)

    async def _run_dissemination(self) -> None:
        while True:
            target = self.members.get_target()
            asyncio.create_task(self._disseminate(target))
            await asyncio.sleep(self.config.sync_period)

    async def _run_suspect_timeout(self) -> None:
        while True:
            before = time.time()
            await asyncio.sleep(self.config.suspect_period)
            for member in self.members.get_all(Status.SUSPECT):
                if member.status_change < before:
                    self.members.notify(member, new_status=Status.OFFLINE)

    async def run(self) -> NoReturn:
        await asyncio.gather(
            self._run_handler(),
            self._run_failure_detection(),
            self._run_dissemination(),
            self._run_suspect_timeout())
        raise RuntimeError()
