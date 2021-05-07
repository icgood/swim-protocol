
from __future__ import annotations

import random
import time
from collections import defaultdict
from collections.abc import Generator, Iterator, Mapping, Set
from functools import total_ordering
from typing import Final, Optional, Any
from weakref import WeakKeyDictionary, WeakValueDictionary

from .config import BaseConfig
from .listener import Listener
from .shuffle import Shuffle, WeakShuffle
from .status import Status

__all__ = ['Member', 'Members']


@total_ordering
class Member:
    """Represents a :term:`member` node of the cluster."""

    #: Before a non-local cluster member metadata has been initialized with a
    #: known value, it is assigned this empty :class:`dict` for
    #: `identity comparisons
    #: <https://docs.python.org/3/reference/expressions.html#is-not>`_.
    METADATA_UNKNOWN: Mapping[str, bytes] = {}

    def __init__(self, name: str, local: bool) -> None:
        super().__init__()
        self.name: Final = name
        self.local: Final = local
        self._clock = 0
        self._validity = random.randbytes(8)
        self._known_clocks: WeakKeyDictionary[Member, int] = \
            WeakKeyDictionary()
        self._status = Status.OFFLINE
        self._status_time = time.time()
        self._metadata: frozenset[tuple[str, bytes]] = frozenset()
        self._metadata_dict = self.METADATA_UNKNOWN
        self._pending_clock: Optional[int] = None
        self._pending_status: Optional[Status] = None
        self._pending_metadata: Optional[frozenset[tuple[str, bytes]]] = None

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
        return f'Member<{self.name} {self.status.name}>'

    @property
    def source(self) -> tuple[str, bytes]:
        return self.name, self._validity

    @property
    def clock(self) -> int:
        """The :term:`sequence clock` tracking changes distributed across the
        cluster.  This value is always increasing, as changes are made to the
        member status or metadata.

        """
        return self._clock

    @property
    def status(self) -> Status:
        """The last known :term:`status` of the cluster member."""
        return self._status

    @property
    def status_time(self) -> float:
        """The local system time when :attr:`.status` last changed."""
        return self._status_time

    @property
    def metadata(self) -> Mapping[str, bytes]:
        """The last known :term:`metadata` of the cluster member."""
        return self._metadata_dict

    def _needs_gossip(self, member: Member) -> bool:
        known_clock = self._known_clocks.get(member, -1)
        return member.clock > known_clock

    def _set_clock(self, clock: int, next_clock: int) -> None:
        assert self._pending_clock is None
        if clock > self._clock:
            self._pending_clock = clock

    def _set_status(self, status: Status) -> None:
        assert self._pending_status is None
        transition = self._status.transition(status)
        if transition != self._status:
            self._pending_status = transition

    def _set_metadata(self, metadata: Mapping[str, bytes]) -> None:
        assert self._pending_metadata is None
        pending_metadata = frozenset(metadata.items())
        if pending_metadata != self._metadata:
            self._pending_metadata = pending_metadata

    def _save(self, source: Optional[Member], next_clock: int) -> bool:
        updated = False
        ignore_update = self.local and source is not None
        pending_clock = self._pending_clock
        pending_status = self._pending_status
        pending_metadata = self._pending_metadata
        self._pending_clock = None
        self._pending_status = None
        self._pending_metadata = None
        if pending_clock is None and self != source:
            return False
        elif ignore_update:
            pending_clock = next_clock
        if pending_status is not None:
            updated = True
            if not ignore_update:
                self._status = pending_status
                self._status_time = time.time()
        if pending_metadata is not None:
            updated = True
            if not ignore_update:
                self._metadata = pending_metadata
                self._metadata_dict = dict(pending_metadata)
        if updated and pending_clock is not None:
            self._clock = pending_clock
        return updated


class Members(Set[Member]):
    """Manages the :term:`members <member>` of the cluster.

    Args:
        config: The cluster config object.

    """

    def __init__(self, config: BaseConfig) -> None:
        super().__init__()
        self.listener: Final = Listener(Member)
        self._next_clock = 1
        self._local = Member(config.local_name, True)
        self._non_local: set[Member] = set()
        self._members = WeakValueDictionary({config.local_name: self._local})
        self._statuses: defaultdict[Status, WeakShuffle[Member]] = \
            defaultdict(WeakShuffle)
        for peer in config.peers:
            self.get(peer)
        self.update(self._local, new_status=Status.ONLINE,
                    new_metadata=config.local_metadata)

    def __contains__(self, val: object) -> bool:
        return val in self._members

    def __iter__(self) -> Iterator[Member]:
        return self._members.values()

    def __len__(self) -> int:
        return len(self._members)

    def _refresh_statuses(self, member: Member) -> None:
        if not member.local:
            member_status = member.status
            for status in Status:
                if member_status & status:
                    self._statuses[status].add(member)
                else:
                    self._statuses[status].discard(member)

    @property
    def local(self) -> Member:
        """The :term:`local member` for the process."""
        return self._local

    @property
    def non_local(self) -> Set[Member]:
        """All of the non-local cluster :term:`members <member>`."""
        return self._non_local

    def find(self, count: int, *, status: Status = Status.ALL,
             exclude: Set[Member] = frozenset()) -> frozenset[Member]:
        """Return a randomly-chosen subset of non-local cluster members that
        meet the given criteria.

        Args:
            count: At most this many members will be returned.
            status: The real or aggregate status of the members.
            exclude: Members that must not be included in the resulting list.

        """
        shuffle = self._statuses[status]
        results: set[Member] = set()
        num_excluded = sum(1 for member in exclude if member in shuffle)
        num_remaining = len(shuffle) - num_excluded
        num_results = min(num_remaining, count)
        while len(results) < num_results:
            results.add(shuffle.choice())
        return frozenset(results)

    def get_status(self, status: Status) -> Shuffle[Member]:
        """Return all of the non-local cluster members with the given status.

        Args:
            status: A real status like
                :attr:`~swimprotocol.status.Status.ONLINE` or an aggregate
                status like :attr:`~swimprotocol.status.Status.AVAILABLE`.

        """
        return self._statuses[status]

    def get(self, name: str, validity: Optional[bytes] = None) -> Member:
        """Return the cluster member with the given name, creating it if does
        not exist.

        If *validity* is given and *name* matches an existing non-local member,
        it is compared to the previous validity value, causing a full
        resynchronize if they are different.

        Args:
            name: The unique name of the cluster member.
            validity: Random bytes used to check existing member validity.

        """
        member = self._members.get(name)
        if member is None:
            member = Member(name, False)
            self._non_local.add(member)
            self._members[name] = member
            for status in Status:
                if member.status & status:
                    self._statuses[status].add(member)
        if not member.local and validity is not None \
                and member._validity != validity:
            member._known_clocks.clear()
            member._validity = validity
        return member

    def _update(self, member: Member, source: Optional[Member],
                clock: int, status: Optional[Status],
                metadata: Optional[Mapping[str, bytes]]) -> None:
        next_clock = self._next_clock
        member._set_clock(clock, next_clock)
        if status is not None:
            member._set_status(status)
        if metadata is not None:
            member._set_metadata(metadata)
        if member._save(source, next_clock):
            self._refresh_statuses(member)
            self.listener.notify(member)
        if member.clock >= next_clock:
            self._next_clock = member.clock + 1

    def update(self, member: Member, *,
               new_status: Optional[Status] = None,
               new_metadata: Optional[Mapping[str, bytes]] = None) -> None:
        """Update the cluster member status or metadata.

        Args:
            member: The cluster member to update.
            new_status: A new status for the member, if any.
            new_metadata: New metadata dictionary for the member, if any.

        """
        self._update(member, None, self._next_clock, new_status, new_metadata)

    def apply(self, member: Member, source: Member, clock: int, *,
              status: Status, metadata: Optional[Mapping[str, bytes]]) \
            -> None:
        """Apply a disseminated update from *source* to *member*.

        Args:
            member: The cluster member to update.
            source: The cluster member that disseminated the update.
            clock: The sequence clock of the update.
            status: The status to apply to *member*.
            metadata: The metadata to apply to *member*, if known.

        """
        self._update(member, source, clock, status, metadata)

    def get_gossip(self, target: Member) -> Generator[Member, None, None]:
        """Iterates through cluster members looking for :term:`gossip` that
        should be sent to *target*.

        See Also:
            :ref:`Dissemination`

        Args:
            target: The recipient of the cluster gossip.

        """
        local = self._local
        if target._needs_gossip(local):
            yield local
        for member in self._non_local:
            if member.metadata is not Member.METADATA_UNKNOWN and \
                    target._needs_gossip(member):
                yield member

    def ack_gossip(self, member: Member, source: Member, clock: int) -> None:
        """Marks the *source* cluster member as having received updates about
        *member* up to the given sequence clock. This prevents repeated
        transfer of known gossip.

        Args:
            member: The cluster member that was updated.
            source: The cluster member that received the update.
            clock: The sequence clock of the update.

        """
        assert clock <= self._next_clock
        source._known_clocks[member] = clock
