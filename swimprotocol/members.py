
from __future__ import annotations

import random
import time
from collections import defaultdict
from collections.abc import Collection, Sequence, Mapping
from functools import total_ordering
from typing import Final, Optional, Any
from weakref import WeakSet, WeakValueDictionary

from .config import Config
from .listener import Listener
from .status import Status

__all__ = ['Member', 'Members']


@total_ordering
class Member:
    """Represents a member node of the cluster."""

    #: Before a non-local cluster member metadata has been initialized with a
    #: known value, it is assigned this empty :class:`dict` for
    #: `identity comparisons
    #: <https://docs.python.org/3/reference/expressions.html#is-not>`_.
    METADATA_UNKNOWN: Mapping[bytes, bytes] = {}

    def __init__(self, name: str, index: int, local: bool) -> None:
        super().__init__()
        self.name: Final = name
        self.index: Final = index
        self.local: Final = local
        self._clock = 0
        self._status = Status.OFFLINE
        self._status_time = time.time()
        self._metadata: frozenset[tuple[bytes, bytes]] = frozenset()
        self._metadata_dict = self.METADATA_UNKNOWN
        self._pending_clock: Optional[int] = None
        self._pending_status: Optional[Status] = None
        self._pending_metadata: Optional[frozenset[tuple[bytes, bytes]]] = None

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
        """The sequence clock tracking changes distributed across the cluster.
        This value is always increasing, as changes are made to the member
        status or metadata.

        """
        return self._clock

    @property
    def status(self) -> Status:
        """The last known status of the cluster member."""
        return self._status

    @property
    def status_time(self) -> float:
        """The local system time when :attr:`.status` last changed."""
        return self._status_time

    @property
    def metadata(self) -> Mapping[bytes, bytes]:
        """The last known metadata of the cluster member."""
        return self._metadata_dict

    def _set_clock(self, clock: int) -> None:
        assert self._pending_clock is None
        if clock > self._clock:
            self._pending_clock = clock

    def _set_status(self, status: Status) -> None:
        assert self._pending_status is None
        transition = self._status.transition(status)
        if transition != self._status:
            self._pending_status = transition

    def _set_metadata(self, metadata: Mapping[bytes, bytes]) -> None:
        assert self._pending_metadata is None
        pending_metadata = frozenset(metadata.items())
        if pending_metadata != self._metadata:
            self._pending_metadata = pending_metadata

    def _save(self) -> bool:
        updated = False
        pending_clock = self._pending_clock
        pending_status = self._pending_status
        pending_metadata = self._pending_metadata
        if pending_clock is None:
            self._pending_status = None
            self._pending_metadata = None
            return False
        if pending_status is not None:
            updated = True
            self._status = pending_status
            self._status_time = time.time()
            self._pending_status = None
        if pending_metadata is not None:
            updated = True
            self._metadata = pending_metadata
            self._metadata_dict = dict(pending_metadata)
            self._pending_metadata = None
        if updated:
            self._clock = pending_clock
        self._pending_clock = None
        return updated


class Members:
    """Manages the members of the cluster.

    Args:
        config: The cluster config object.

    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.listener: Final = Listener(Member)
        self._next_clock = 1
        self._local = Member(config.local_name, -1, True)
        self._non_local: list[Member] = []
        self._members = WeakValueDictionary({config.local_name: self._local})
        self._statuses: defaultdict[Status, WeakSet[Member]] = \
            defaultdict(WeakSet)
        for peer in config.peers:
            self.get(peer)
        self.update(self._local, new_status=Status.ONLINE,
                    new_metadata=config.local_metadata)

    def _refresh_statuses(self, member: Member,
                          before: Status, after: Status) -> None:
        for status in Status:
            if before & status and not after & status:
                self._statuses[status].discard(member)
            elif not before & status and after & status:
                self._statuses[status].add(member)

    @property
    def local(self) -> Member:
        """The cluster member for the local instance."""
        return self._local

    @property
    def non_local(self) -> Sequence[Member]:
        """All of the non-local cluster members."""
        return list(self._non_local)

    @property
    def all(self) -> Sequence[Member]:
        """All of the cluster members, local and non-local."""
        return list(self._members.values())

    def get_target(self) -> Member:
        """Return a random non-local cluster member."""
        return random.choice(self._non_local)

    def get_targets(self, count: int, exclude: Collection[Member]) \
            -> Sequence[Member]:
        """Return a sub-set of non-local cluster members.

        Args:
            count: The number of members to choose.
            exclude: Members that must not be included in the resulting list.

        """
        indexes: set[int] = set()
        exclude_indexes = {member.index for member in exclude}
        non_local = self._non_local
        num_results = min(len(non_local) - len(exclude), count)
        while len(indexes) < num_results:
            idx = random.randrange(0, len(non_local))
            if idx not in exclude_indexes:
                indexes.add(idx)
        return [non_local[idx] for idx in indexes]

    def get_status(self, status: Status) -> frozenset[Member]:
        """Return all of the cluster members with the given status.

        Args:
            status: A real status like
                :attr:`~swimprotocol.packet.Status.ONLINE` or an aggregate
                status like :attr:`~swimprotocol.packet.Status.AVAILABLE`.

        """
        return frozenset(self._statuses[status])

    def get(self, name: str) -> Member:
        """Return the cluster member with the given name, creating it if does
        not exist.

        Args:
            The unique name of the cluster member.

        """
        member = self._members.get(name)
        if member is None:
            index = len(self._non_local)
            member = Member(name, index, False)
            self._non_local.append(member)
            self._members[name] = member
        return member

    def update(self, member: Member, clock: Optional[int] = None, *,
               new_status: Optional[Status] = None,
               new_metadata: Optional[Mapping[bytes, bytes]] = None) -> None:
        """Update the cluster member status or metadata.

        Args:
            member: The cluster member to update.
            clock: The sequence clock for the update, or ``None`` to assign the
                next available.
            new_status: A new status for the member, if any.
            new_metadata: New metadata dictionary for the member, if any.

        """
        if clock is None:
            clock = self._next_clock
        elif member.local:
            return
        before_status = member.status
        member._set_clock(clock)
        if new_status is not None:
            member._set_status(new_status)
        if new_metadata is not None:
            member._set_metadata(new_metadata)
        if member._save():
            self._refresh_statuses(member, before_status, member.status)
            if member.clock >= self._next_clock:
                self._next_clock += 1
            self.listener.notify(member)

    def get_gossip(self, target: Member, count: int) -> Sequence[Member]:
        """Iterates through cluster members looking for changes that should be
        sent to *target*. Cluster members are returned if their
        :attr:`~Member.clock` is higher than the *target* clock.

        Args:
            target: The recipient of the cluster gossip.
            count: Minimum number of members to return, if possible.

        """
        local = self._local
        results = []
        if local.clock > target.clock:
            results.append(local)
        for member in self._non_local:
            if member != target and member.clock > target.clock:
                results.append(member)
        remaining = count - len(results)
        if remaining > 0:
            results.extend(self.get_targets(remaining, results))
        return results
