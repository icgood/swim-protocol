
from __future__ import annotations

import random
from collections.abc import Sequence, Mapping
from typing import Final, Union, Optional, Any
from weakref import WeakSet

from .config import Config
from .listener import Listener
from .types import Address, Status, Update, Gossip

__all__ = ['Member', 'Members']


class Member:

    def __init__(self, config: Config, members: Members, address: Address,
                 metadata: Mapping[str, str], index: int, local: bool) -> None:
        super().__init__()
        self.config: Final = config
        self.members: Final = members
        self.index: Final = index
        self.local: Final = local
        self.address: Final = address
        self._metadata = metadata
        self._metadata_set = frozenset(metadata.items())
        self._status = Status.ONLINE if local else Status.OFFLINE
        self._clock = 0
        self._modified: Optional[int] = None
        self._should_notify = False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Member):
            return self.address == other.address
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.address)

    def __repr__(self) -> str:
        return f'Member<{self.address}>'

    @property
    def modified(self) -> int:
        return self._modified or 0

    @modified.setter
    def modified(self, modified: int) -> None:
        cur_mod = self._modified
        if cur_mod is None or modified > cur_mod:
            self._modified = modified

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, status: Status) -> None:
        if status != self._status:
            if status == Status.OFFLINE:
                self.members._offline.add(self)
                self.members._online.discard(self)
            else:
                self.members._offline.discard(self)
                self.members._online.add(self)
            self._status = status
            self._should_notify = True

    @property
    def metadata(self) -> Mapping[str, str]:
        return self._metadata

    @metadata.setter
    def metadata(self, metadata: Mapping[str, str]) -> None:
        metadata_set = frozenset(metadata.items())
        if metadata_set != self._metadata_set:
            self._metadata = metadata
            self._metadata_set = metadata_set
            self._should_notify = True

    def _notify(self) -> None:
        if self._should_notify:
            self._should_notify = False
            self.members.listener.notify(self.update)

    @property
    def update(self) -> Update:
        return Update(address=self.address, modified=self._modified,
                      status=self._status, metadata=self.metadata)

    def apply(self, update: Update, next_clock: int) -> bool:
        cur_mod = self._modified
        update_mod = update.modified
        if cur_mod is None or update_mod is None or update_mod > cur_mod:
            if update_mod is not None:
                self.modified = update_mod
            elif cur_mod is None:
                self.modified = next_clock
            self.metadata = update.metadata
            self.status = update.status
            self._notify()
            return True
        else:
            return False

    def set_status(self, online: bool, next_clock: int) -> bool:
        status = Status.ONLINE if online else Status.OFFLINE
        if status != self._status:
            self.modified = next_clock
            self.status = status
            self._notify()
            return True
        else:
            return False


class Members:

    def __init__(self, config: Config, peers: Sequence[Address]) -> None:
        super().__init__()
        self.config: Final = config
        self.listener: Final = Listener()
        self._clock = 0
        self._local = Member(config, self, config.local_address,
                             config.local_metadata, -1, True)
        self._members = {config.local_address: self._local}
        self._non_local: list[Member] = []
        self._online: WeakSet[Member] = WeakSet()
        self._offline: WeakSet[Member] = WeakSet()
        for peer in peers:
            self.get(peer)

    @property
    def local(self) -> Member:
        return self._local

    @property
    def non_local(self) -> Sequence[Member]:
        return self._non_local

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

    def get(self, address: Union[str, Address]) -> Member:
        if isinstance(address, str):
            address = Address.parse(address)
        member = self._members.get(address)
        if member is None:
            index = len(self._non_local)
            member = Member(self.config, self, address, {}, index, False)
            self._non_local.append(member)
            self._members[address] = member
        return member

    def set_status(self, target: Member, online: bool) -> None:
        next_clock = self._clock + 1
        if target.set_status(online, next_clock):
            self._clock = next_clock

    def apply(self, gossip: Gossip) -> Member:
        source = self.get(gossip.source)
        source._clock = gossip.clock
        next_clock = max(self._clock, gossip.clock) + 1
        updated = False
        for update in gossip.updates:
            if self.get(update.address).apply(update, next_clock):
                updated = True
        if updated:
            self._clock = next_clock
        return source

    def get_gossip(self, target: Member) -> Gossip:
        local = self._local
        updates = []
        updates.append(local.update)
        for member in self._non_local:
            if member != target and member.modified > target._clock:
                updates.append(member.update)
        return Gossip(source=local.address, clock=self._clock, updates=updates)
