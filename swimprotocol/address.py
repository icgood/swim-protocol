
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

__all__ = ['Address', 'AddressParser']


@dataclass(frozen=True, order=True)
class Address:
    host: str
    port: int

    @classmethod
    def get(cls, addr: tuple[str, int]) -> Address:
        return cls(addr[0], addr[1])

    def __str__(self) -> str:
        return ':'.join((self.host, str(self.port)))


class AddressParser:

    def __init__(self, address_type: type[Address] = Address, *,
                 default_host: Optional[str] = None,
                 default_port: Optional[int] = None) -> None:
        super().__init__()
        self.address_type: Final = address_type
        self.default_host: Final = default_host
        self.default_port: Final = default_port

    def parse(self, address: str) -> Address:
        host, sep, port = address.rpartition(':')
        if sep != ':':
            default_port = self.default_port
            if default_port is not None:
                return self.address_type(host, default_port)
        else:
            default_host = self.default_host
            if host:
                return self.address_type(host, int(port))
            elif default_host is not None:
                return self.address_type(default_host, int(port))
        raise ValueError(address)
