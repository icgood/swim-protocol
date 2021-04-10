
from __future__ import annotations

from argparse import Namespace
from collections.abc import Mapping
from ssl import SSLContext
from typing import Final, Optional

from . import Address

__all__ = ['Config']


class Config:

    def __init__(self, args: Namespace) -> None:
        super().__init__()
        local_address: Address = args.local
        local_metadata: Mapping[str, str] = args.metadata
        self.local_address: Final = local_address
        self.local_metadata: Final = local_metadata

    @property
    def ssl_context(self) -> Optional[SSLContext]:
        return None

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
        return 0.3

    @property
    def sync_timeout(self) -> float:
        return 0.5

    @property
    def introduce_period(self) -> float:
        return 0.5

    @property
    def introduce_timeout(self) -> float:
        return 1.0
