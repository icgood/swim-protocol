
from __future__ import annotations

from argparse import Namespace
from collections.abc import Mapping, Sequence
from typing import Final, Union

from .sign import Signatures

__all__ = ['Config']


class Config:
    """Configure the cluster behavior and characteristics.

    Args:
        args: Command-line arguments namespace.
        secret: The shared secret for cluster packet signatures.
        local_name: The unique name of the local cluster member.
        local_metadata: The local cluster member metadata.
        peers: At least one name of another known node in the cluster.
        ping_interval: Time between :term:`ping` attempts to random cluster
            members.
        ping_timeout: Time to wait for an :term:`ack` after sending a
            :term:`ping`.
        ping_req_count: Number of nodes to send a :term:`ping-req` when a
            :term:`ping` fails.
        ping_req_timeout: Time to wait for an *ack* after sending a
            :term:`ping-req`.
        suspect_timeout: Time to wait after losing connectivity with a cluster
            member before marking it offline.
        sync_interval: Time between sync attempts to disseminate cluster
            changes.

    """

    def __init__(self, args: Namespace, *,
                 secret: Union[str, bytes],
                 local_name: str,
                 local_metadata: Mapping[bytes, bytes],
                 peers: Sequence[str],
                 ping_interval: float = 1.0,
                 ping_timeout: float = 0.3,
                 ping_req_count: int = 1,
                 ping_req_timeout: float = 0.9,
                 suspect_timeout: float = 5.0,
                 sync_interval: float = 0.5) -> None:
        super().__init__()
        self.args: Final = args
        self._signatures = Signatures(secret)
        self.local_name: Final = local_name
        self.local_metadata: Final = local_metadata
        self.peers: Final = peers
        self.ping_interval: Final = ping_interval
        self.ping_timeout: Final = ping_timeout
        self.ping_req_count: Final = ping_req_count
        self.ping_req_timeout: Final = ping_req_timeout
        self.suspect_timeout: Final = suspect_timeout
        self.sync_interval: Final = sync_interval

    @classmethod
    def from_args(cls, args: Namespace) -> Config:
        """Build a :class:`Config` from command-line arguments and sensible
        defaults.

        Args:
            args: The command-line arguments namespace.

        """
        return cls(args, secret=args.secret,
                   local_name=args.local,
                   local_metadata=dict(args.metadata),
                   peers=args.peers)

    @property
    def signatures(self) -> Signatures:
        """Generates and verifies cluster packet signatures."""
        return self._signatures
