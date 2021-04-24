
from __future__ import annotations

import asyncio
from argparse import ArgumentParser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, closing
from typing import Final, Optional

from .protocol import SwimProtocol
from .pack import UdpPack
from ..address import AddressParser
from ..config import Config
from ..members import Members
from ..transport import Transport
from ..worker import Worker

__all__ = ['UdpTransport']


class UdpTransport(Transport):
    """Implements :class:`~swimprotocol.transport.Transport` using UDP, without
    `broadcast <https://en.wikipedia.org/wiki/Broadcast_address>`_.

    This transport assumes that the name of each cluster member is in
    ``host:port`` format, and that any cluster member can receive UDP packets
    from any other cluster member.

    Args:
        config: The cluster configuration object.

    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config: Final = config
        self.args: Final = config.args
        self.address_parser: Final = AddressParser(
            default_host=config.args.udp_host,
            default_port=config.args.udp_port)
        self.udp_pack: Final = UdpPack(config.signatures)
        self._local_address = self.address_parser.parse(config.local_name)

    @property
    def bind_host(self) -> str:
        """The local bind address used to open the UDP socket to receive
        packets.

        See Also:
            :func:`asyncio.loop.create_datagram_endpoint`

        """
        bind: Optional[str] = self.args.udp_bind
        return bind or self._local_address.host

    @property
    def bind_port(self) -> int:
        """The local bind port used to open the UDP socket to receive packets.

        See Also:
            :func:`asyncio.loop.create_datagram_endpoint`

        """
        return self._local_address.port

    @asynccontextmanager
    async def enter(self, members: Members) -> AsyncIterator[Worker]:
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: SwimProtocol(self.address_parser, self.udp_pack),
            reuse_port=True, local_addr=(self.bind_host, self.bind_port))
        assert isinstance(protocol, SwimProtocol)
        worker = Worker(self.config, members, protocol)
        with closing(transport):
            yield worker

    @classmethod
    def add_arguments(cls, name: str, parser: ArgumentParser) -> None:
        group = parser.add_argument_group(f'{name} options')
        group.add_argument('--udp-bind', metavar='INTERFACE',
                           help='The bind IP address.')
        group.add_argument('--udp-host', metavar='NAME',
                           help='The default remote hostname.')
        group.add_argument('--udp-port', metavar='NUM', type=int,
                           help='The default port number.')

    @classmethod
    def init(cls, config: Config) -> Transport:
        return cls(config)
