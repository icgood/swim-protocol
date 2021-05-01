
from __future__ import annotations

from enum import auto, Flag

__all__ = ['Status']


class Status(Flag):
    """Possible cluster member :term:`status` values, as well as aggregate
    values that can be used with bitwise operations but must not be assigned.

    """

    #: The member is responding as expected.
    ONLINE = auto()

    #: The member has stopped responding for long enough to avoid false
    #: positives.
    OFFLINE = auto()

    #: The member has failed to respond, but is not yet declared fully offline.
    SUSPECT = auto()

    #: Aggregate status for statuses that are considered responding,
    #: :attr:`.ONLINE` and :attr:`.SUSPECT`, for use with bitwise operations.
    AVAILABLE = ONLINE | SUSPECT

    #: Aggregate status for statuses that are not considered responding,
    #: :attr:`.OFFLINE` and :attr:`.SUSPECT`, for use with bitwise operations.
    UNAVAILABLE = OFFLINE | SUSPECT

    #: Aggregate status for all statuses, for use with bitwise operations.
    ALL = AVAILABLE | UNAVAILABLE

    def transition(self, to: Status) -> Status:
        """Prevents impossible status transitions, returning a new status to
        be used instead of *to*.

        * :attr:`~Status.OFFLINE` to :attr:`~Status.SUSPECT`, which should
          remain on :attr:`~Status.OFFLINE`.
        * :attr:`~Status.ONLINE` to :attr:`~Status.OFFLINE`, which should first
          go to :attr:`~Status.SUSPECT`.

        Args:
            to: The desired transition status.

        Raises:
            ValueError: *to* was an aggregate status, which cannot be
                transitioned to directly.

        """
        if to == Status.AVAILABLE or to == Status.UNAVAILABLE:
            raise ValueError(to)
        elif to == Status.SUSPECT and self == Status.OFFLINE:
            return self
        elif to == Status.OFFLINE and self == Status.ONLINE:
            return Status.SUSPECT
        else:
            return to
