
from __future__ import annotations

import asyncio
from typing import Final, NoReturn

from .config import Config
from .members import Members
from .transport import Client
from .types import Gossip, Handlers
from .util import as_available

__all__ = ['Worker']


class Worker(Handlers):

    def __init__(self, config: Config, members: Members,
                 client: Client) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members
        self.client: Final = client

    async def handle_ping(self) -> bool:
        return True

    async def handle_ping_req(self, target: str) -> bool:
        member = self.members.get(target)
        return await self.client.ping(member)

    async def handle_sync(self, gossip: Gossip) -> Gossip:
        source = self.members.apply(gossip)
        return self.members.get_gossip(source)

    async def _run_introductions(self) -> None:
        ready = False
        while not ready:
            pending_intros = {
                self.client.sync(target, self.members.get_gossip(target))
                for target in self.members.non_local}
            async for gossip in as_available(pending_intros):
                if gossip is not None:
                    self.members.apply(gossip)
                    ready = True
            if not ready:
                await asyncio.sleep(self.config.sync_period)

    async def _run_failure_detection(self) -> None:
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
            self.members.set_status(target, online)

    async def _run_dissemination(self) -> None:
        while True:
            await asyncio.sleep(self.config.sync_period)
            target = self.members.get_target()
            my_gossip = self.members.get_gossip(target)
            their_gossip = await self.client.sync(target, my_gossip)
            if their_gossip is not None:
                self.members.apply(their_gossip)

    async def run(self) -> NoReturn:
        await self._run_introductions()
        await asyncio.gather(
            self._run_failure_detection(),
            self._run_dissemination())
        raise RuntimeError()
