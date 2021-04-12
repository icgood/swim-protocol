
from __future__ import annotations

import asyncio
from asyncio import Event, Task
from typing import Final

from .config import Config
from .members import Members
from .transport import Client
from .types import Update, Gossip, Handlers
from .util import as_available

__all__ = ['Worker']


class Worker(Handlers):

    def __init__(self, config: Config, members: Members,
                 client: Client) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members
        self.client: Final = client
        self._ready = Event()

    async def handle_ping(self) -> bool:
        await self._ready.wait()
        return True

    async def handle_ping_req(self, target: str) -> bool:
        await self._ready.wait()
        member = self.members.get(target)
        return await self.client.ping(member)

    async def handle_introduce(self, update: Update) -> Gossip:
        return self.members.introduce(update)

    async def handle_sync(self, gossip: Gossip) -> Gossip:
        await self._ready.wait()
        source = self.members.apply(gossip)
        return self.members.get_gossip(source)

    async def _run_introductions(self) -> None:
        local_update = self.members.local.update
        ready = self._ready
        while not ready.is_set():
            pending_intros = {
                self.client.introduce(target, local_update)
                for target in self.members.non_local}
            async for intro_gossip in as_available(pending_intros):
                if intro_gossip is not None:
                    self.members.apply(intro_gossip)
                    ready.set()
            if not ready.is_set():
                await asyncio.sleep(self.config.introduce_period)

    async def _run_failure_detection(self) -> None:
        await self._ready.wait()
        while True:
            await asyncio.sleep(self.config.ping_period)
            target = self.members.get_target()
            online = await self.client.ping(target)
            if not online:
                indirects = self.members.get_indirect(target)
                pending_ping_reqs = {
                    self.client.ping_req(indirect, target)
                    for indirect in indirects}
                async for online in as_available(pending_ping_reqs):
                    if online:
                        break
            target.set_status(online)

    async def _run_dissemination(self) -> None:
        while True:
            await asyncio.sleep(self.config.sync_period)
            target = self.members.get_target()
            my_gossip = self.members.get_gossip(target)
            their_gossip = await self.client.sync(target, my_gossip)
            if their_gossip is not None:
                self.members.apply(their_gossip)

    async def _run(self) -> None:
        await asyncio.gather(
            self._run_failure_detection(),
            self._run_dissemination())

    async def start(self) -> Task[None]:
        await self._run_introductions()
        return asyncio.create_task(self._run())
