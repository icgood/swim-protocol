
from __future__ import annotations

import asyncio
import time
from abc import abstractmethod
from asyncio import Event, TimeoutError
from collections.abc import Mapping, Sequence
from contextlib import suppress
from typing import Protocol, Final, Optional, NoReturn
from weakref import WeakSet, WeakKeyDictionary

from .config import Config
from .members import Member, Members
from .packet import Packet, Ping, PingReq, Ack, Gossip
from .status import Status

__all__ = ['Worker']


class IO(Protocol):
    """Basic packet send and receive interface that must be provided by
    :class:`~swimprotocol.transport.Transport` implementations.

    """

    @abstractmethod
    async def recv(self) -> Packet:
        """Wait until a packet has been received by the transport layer and
        return it.

        """
        ...

    @abstractmethod
    async def send(self, member: Member, packet: Packet) -> None:
        """Send the given *packet* to another cluster *member*.

        Args:
            member: The recipient cluster member.
            packet: The SWIM protocol packet to send.

        """
        ...


class Worker:
    """Manages the failure detection and dissemination components of the SWIM
    protocol.

    Args:
        config: The cluster configuration object.
        members: Tracks the state of the cluster members.
        io: Provided by the :class:`~swimprotocol.transport.Transport` to send
            and receive :class:`~swimprotocol.packet.Packet` objects.

    """

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
                self._apply_gossip(packet)

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
            count = self.config.ping_req_count
            indirects = self.members.get_targets(count, [target])
            if indirects:
                await asyncio.wait([
                    self.io.send(indirect, PingReq(
                        source=local.name, target=target.name))
                    for indirect in indirects])
                online = await self._wait(target, self.config.ping_req_timeout)
        new_status = Status.ONLINE if online else Status.SUSPECT
        self.members.update(target, new_status=new_status)

    def _build_gossip(self, member: Member) -> Gossip:
        if member.metadata is Member.METADATA_UNKNOWN:
            metadata: Optional[Mapping[bytes, bytes]] = None
        else:
            metadata = member.metadata
        return Gossip(source=self.members.local.name,
                      name=member.name, clock=member.clock,
                      status=member.status, metadata=metadata)

    def _apply_gossip(self, gossip: Gossip) -> None:
        member = self.members.get(gossip.name)
        self.members.update(member, gossip.clock,
                            new_status=gossip.status,
                            new_metadata=gossip.metadata)

    async def _disseminate(self, target: Member) -> None:
        count = self.config.sync_count
        for member in self.members.get_gossip(target, count):
            packet = self._build_gossip(member)
            await self.io.send(target, packet)

    async def _run_failure_detection(self) -> None:
        while True:
            target = self.members.get_target()
            asyncio.create_task(self._check(target))
            await asyncio.sleep(self.config.ping_interval)

    async def _run_dissemination(self) -> None:
        while True:
            target = self.members.get_target()
            asyncio.create_task(self._disseminate(target))
            await asyncio.sleep(self.config.sync_interval)

    async def _run_suspect_timeout(self) -> None:
        while True:
            before = time.time()
            await asyncio.sleep(self.config.suspect_timeout)
            for member in self.members.get_status(Status.SUSPECT):
                if member.status_time < before:
                    self.members.update(member, new_status=Status.OFFLINE)

    async def run(self) -> NoReturn:
        """Indefinitely handle received SWIM protocol packets and, at
        configurable intervals, send failure detection and dissemination
        packets.

        """
        await asyncio.gather(
            self._run_handler(),
            self._run_failure_detection(),
            self._run_dissemination(),
            self._run_suspect_timeout())
        raise RuntimeError()
