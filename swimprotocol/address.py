
from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional

__all__ = ['Address', 'AddressParser']


@dataclass(frozen=True, order=True)
class Address:
    """Manages an address for socket connections.

    Args:
        host: The address hostname string.
        port: The address port number.

    """

    host: str
    port: int

    @classmethod
    def get(cls, addr: tuple[str, int]) -> Address:
        """Return an :class:`Address` from a ``(host, port)`` tuple.

        Args:
            addr: The address tuple from :mod:`socket` functions.

        """
        return cls(addr[0], addr[1])

    def __str__(self) -> str:
        return ':'.join((self.host, str(self.port)))


class AddressParser:
    """Manages the defaults to use when parsing an address string.

    Args:
        address_type: Override the :class:`Address` implementation.
        default_host: The default hostname, if missing from the address string
            (e.g. ``:1234:``).
        default_port: The default port number, if missing from the address
            string (e.g. ``example.tld``).

    """

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
