
from __future__ import annotations

import random
from collections.abc import Generator, Sequence, Mapping
from functools import total_ordering
from typing import Final, Optional, Any

from .config import Config
from .listener import Listener
from .packet import Status, Gossip

__all__ = ['Member', 'Members']


@total_ordering
class Member:

    def __init__(self, config: Config, members: Members, name: str,
                 metadata: Optional[Mapping[bytes, bytes]],
                 index: int, local: bool) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members
        self.name: Final = name
        self.index: Final = index
        self.local: Final = local
        self._metadata = metadata
        self._metadata_set = frozenset(metadata.items() if metadata else [])
        self._status = Status.ONLINE if local else Status.OFFLINE
        self._clock = 0
        self._should_notify = False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Member):
            return self.name == other.name
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Member):
            return self.name < other.name
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        return f'Member<{self.name}>'

    @property
    def clock(self) -> int:
        return self._clock

    @clock.setter
    def clock(self, clock: int) -> None:
        if clock > self._clock:
            self._clock = clock

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, status: Status) -> None:
        if status != self._status:
            self._status = status
            self._should_notify = True

    @property
    def metadata(self) -> Optional[Mapping[bytes, bytes]]:
        return self._metadata

    @metadata.setter
    def metadata(self, metadata: Optional[Mapping[bytes, bytes]]) -> None:
        if metadata is not None:
            metadata_set = frozenset(metadata.items())
            if metadata_set != self._metadata_set:
                self._metadata = metadata
                self._metadata_set = metadata_set
                self._should_notify = True

    @property
    def gossip(self) -> Gossip:
        return Gossip(source=self.members.local.name, clock=self._clock,
                      name=self.name, status=self._status,
                      metadata=self._metadata)

    def apply(self, gossip: Gossip) -> None:
        new_mod = gossip.clock
        if gossip.source == self.name or new_mod > self.clock:
            self.status = gossip.status
            self.metadata = gossip.metadata
        self.clock = new_mod

    def notify(self) -> bool:
        should_notify = self._should_notify
        if should_notify:
            self._should_notify = False
            self.members.listener.notify(self)
        return should_notify


class Members:

    def __init__(self, config: Config, peers: Sequence[str]) -> None:
        super().__init__()
        self.config: Final = config
        self.listener: Final = Listener(Member)
        self._local = Member(config, self, config.local_name,
                             config.local_metadata, -1, True)
        self._members = {config.local_name: self._local}
        self._non_local: list[Member] = []
        for peer in peers:
            self.get(peer)

    @property
    def local(self) -> Member:
        return self._local

    @property
    def non_local(self) -> Sequence[Member]:
        return list(self._non_local)

    @property
    def all(self) -> Sequence[Member]:
        return list(self._members.values())

    @property
    def clock(self) -> int:
        return self.local.clock

    @clock.setter
    def clock(self, clock: int) -> None:
        self.local.clock = clock

    def get_target(self) -> Member:
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

    def get(self, name: str) -> Member:
        member = self._members.get(name)
        if member is None:
            index = len(self._non_local)
            member = Member(self.config, self, name, None, index, False)
            self._non_local.append(member)
            self._members[name] = member
        return member

    def notify(self, target: Member, *,
               new_status: Optional[Status] = None) -> None:
        if new_status is not None:
            target.status = new_status
        next_clock = self.clock + 1
        if target.notify():
            self.clock = target.clock = next_clock

    def apply_gossip(self, gossip: Gossip) -> None:
        source = self.get(gossip.source)
        source.clock = gossip.clock
        member = self.get(gossip.name)
        member.apply(gossip)
        member.notify()
        if gossip.clock > self.clock:
            self.clock = gossip.clock

    def get_gossip(self, target: Member) -> Generator[Gossip, None, None]:
        local = self._local
        yield local.gossip
        for member in self._non_local:
            if member != target and member.clock > target.clock:
                yield member.gossip
