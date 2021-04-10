"""Contains the package version string.

See Also:
    `PEP 396 <https://www.python.org/dev/peps/pep-0396/>`_

"""

from __future__ import annotations

from dataclasses import dataclass

import pkg_resources

__all__ = ['__version__', 'Address']

#: The package version string.
__version__: str = pkg_resources.require('swim-protocol')[0].version


@dataclass(frozen=True)
class Address:
    host: str
    port: int

    def __str__(self) -> str:
        return ':'.join((self.host, str(self.port)))

    @classmethod
    def parse(cls, address: str) -> Address:
        host, sep, port = address.rpartition(':')
        if sep != ':' or not host:
            raise ValueError()
        return cls(host, int(port))
