
from __future__ import annotations

from argparse import Namespace
from collections.abc import Mapping, Sequence
from typing import Final

from .sign import Signatures

__all__ = ['Config']


class Config:

    def __init__(self, args: Namespace) -> None:
        super().__init__()
        self.args: Final = args
        local_name: str = args.local
        local_metadata: Mapping[str, str] = dict(args.metadata)
        self.local_name: Final = local_name
        self.local_metadata: Final = local_metadata
        self.signatures: Final = Signatures(args.secret)

    @property
    def peers(self) -> Sequence[str]:
        peers: list[str] = self.args.peers
        return peers

    @property
    def num_indirect(self) -> int:
        return 1

    @property
    def ping_period(self) -> float:
        return 1.0

    @property
    def ping_timeout(self) -> float:
        return 0.3

    @property
    def ping_req_timeout(self) -> float:
        return 0.9

    @property
    def sync_period(self) -> float:
        return 1.0
