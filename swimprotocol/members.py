
from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Final, Union, Any

from grpclib.client import Channel

from . import Address
from .config import Config
from .grpc.swimprotocol_pb2 import Status, Update, Gossip

__all__ = ['Member', 'Members']


class Member:

    def __init__(self, members: Members, address: Address, index: int,
                 local: bool) -> None:
        super().__init__()
        self.members: Final = members
        self.ssl_context: Final = members.config.ssl_context
        self.index: Final = index
        self.local: Final = local
        self.address: Final = address
        self.metadata: dict[str, str] = {}
        self._status = Status.ONLINE if local else Status.OFFLINE
        self._clock = 1 if local else 0

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Member):
            return self.address == other.address
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.address)

    def __repr__(self) -> str:
        return f'Member<{self.address}>'

    @property
    def host(self) -> str:
        return self.address.host

    @property
    def port(self) -> int:
        return self.address.port

    @property
    def clock(self) -> int:
        return self._clock

    @clock.setter
    def clock(self, clock: int) -> None:
        self._clock = clock
        if clock >= self.members._clock:
            self.members._clock = clock + 1

    @property
    def status(self) -> Status.V:
        return self._status

    @status.setter
    def status(self, status: Status.V) -> None:
        if status != self._status:
            if status == Status.OFFLINE:
                print(f'{self.address!s} is offline: {self.metadata!r}')
            else:
                print(f'{self.address!s} is online: {self.metadata!r}')
            self._status = status

    @property
    def update(self) -> Update:
        return Update(address=str(self.address), clock=self.clock,
                      status=self._status, metadata=self.metadata)

    def get_channel(self) -> Channel:
        return Channel(self.host, self.port, ssl=self.ssl_context)

    def apply(self, update: Update, *, intro: bool = False) -> None:
        if intro or update.clock > self.clock:
            self.clock = self.members._clock if intro else update.clock
            self.metadata.update(update.metadata)
            self.status = update.status

    def set_status(self, online: bool) -> None:
        status = Status.ONLINE if online else Status.OFFLINE
        if status != self._status:
            self.clock = self.members._clock
            self.status = status


class Members:

    def __init__(self, config: Config, peers: Sequence[Address]) -> None:
        super().__init__()
        self.config: Final = config
        self._clock = 0
        self._local = Member(self, config.local_address, -1, True)
        self._local.metadata.update(config.local_metadata)
        self._members = {config.local_address: self._local}
        self._non_local: list[Member] = []
        for peer in peers:
            self.get(peer)

    @property
    def local(self) -> Member:
        return self._local

    @property
    def non_local(self) -> Sequence[Member]:
        return self._non_local

    def get_target(self) -> Member:
        assert len(self._non_local) > 0
        return random.choice(self._non_local)

    def get_indirect(self, target: Member) -> Sequence[Member]:
        indexes: set[int] = set()
        target_idx = target.index
        non_local = self._non_local
        num_indirect = min(len(non_local) - 1, self.config.num_indirect)
        while len(indexes) < num_indirect:
            idx = random.randrange(0, len(non_local))
            if idx != target_idx:
                indexes.add(idx)
        return [non_local[idx] for idx in indexes]

    def get(self, address: Union[str, Address]) -> Member:
        if isinstance(address, str):
            address = Address.parse(address)
        member = self._members.get(address)
        if member is None:
            index = len(self._non_local)
            member = Member(self, address, index, False)
            self._non_local.append(member)
            self._members[address] = member
        return member

    def introduce(self, update: Update) -> Gossip:
        member = self.get(update.address)
        member.apply(update, intro=True)
        return self.get_gossip(member)

    def apply(self, gossip: Gossip) -> Member:
        source = self.get(gossip.source)
        for update in gossip.updates:
            self.get(update.address).apply(update)
        return source

    def get_gossip(self, target: Member) -> Gossip:
        local = self._local
        updates = []
        clock = target.clock
        updates.append(local.update)
        for member in self._non_local:
            if member.clock > clock:
                updates.append(member.update)
        return Gossip(source=str(local.address), updates=updates)
