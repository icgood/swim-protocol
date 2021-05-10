
from __future__ import annotations

import asyncio
import socket
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence, AsyncIterator
from contextlib import asynccontextmanager, closing, suppress
from typing import Final, Any, Optional

from .protocol import SwimProtocol
from .pack import UdpPack
from ..address import Address, AddressParser
from ..config import BaseConfig, ConfigError, TransientConfigError
from ..members import Members
from ..transport import Transport
from ..worker import Worker

__all__ = ['UdpConfig', 'UdpTransport']


class UdpConfig(BaseConfig):
    """Implements :class:`~swimprotocol.config.BaseConfig`, adding additional
    configuration required for :class:`UdpTransport`.

    Args:
        bind_host: The hostname or IP address to bind the UDP socket. The
            hostname from the *local_name* address is used by default.
        bind_port: The port number to bind the UDP socket. The port from the
            *local_name* address is used by default.
        default_host: The hostname or IP address to connect to if an address
            string does not specify a hostname, e.g. ``':1234'``.
        default_port: The port number to connect to if an address string does
            not specify a port number, e.g. ``'myhost'``.
        discovery: Resolve the local address as a DNS **A**/**AAAA** record
            containing peers. The local IP address will also be auto-discovered
            by attempting to :meth:`~socket.socket.connect` to the hostname.
        kwargs: Additional keyword arguments passed to the
            :class:`~swimprotocol.config.BaseConfig` constructor.

    """

    def __init__(self, *, bind_host: Optional[str] = None,
                 bind_port: Optional[int] = None,
                 default_host: Optional[str] = None,
                 default_port: Optional[int] = None,
                 discovery: bool = False,
                 **kwargs: Any) -> None:
        address_parser = AddressParser(
            default_host=default_host,
            default_port=default_port)
        if discovery:
            self._discover(address_parser, kwargs)
        super().__init__(**kwargs)
        self.bind_host: Final = bind_host
        self.bind_port: Final = bind_port
        self.address_parser: Final = address_parser

    @classmethod
    def add_arguments(cls, parser: ArgumentParser, *,
                      prefix: str = '--') -> None:
        super().add_arguments(parser, prefix=prefix)
        group = parser.add_argument_group('swim udp options')
        group.add_argument(f'{prefix}udp-bind', metavar='INTERFACE',
                           dest='swim_udp_bind',
                           help='The bind IP address.')
        group.add_argument(f'{prefix}udp-bind-port', metavar='NUM',
                           dest='swim_udp_bind_port',
                           help='The bind port.')
        group.add_argument(f'{prefix}udp-host', metavar='NAME',
                           dest='swim_udp_host',
                           help='The default remote hostname.')
        group.add_argument(f'{prefix}udp-port', metavar='NUM', type=int,
                           dest='swim_udp_port',
                           help='The default port number.')
        group.add_argument(f'{prefix}udp-discovery', action='store_true',
                           dest='swim_udp_discovery',
                           help='Find cluster with DNS discovery.')

    @classmethod
    def parse_args(cls, args: Namespace, *, env_prefix: str = 'SWIM') \
            -> dict[str, Any]:
        kwargs = super().parse_args(args, env_prefix=env_prefix)
        return kwargs | {
            'bind_host': args.swim_udp_bind,
            'bind_port': args.swim_udp_bind_port,
            'default_host': args.swim_udp_host,
            'default_port': args.swim_udp_port,
            'discovery': args.swim_udp_discovery}

    @classmethod
    def _discover(cls, address_parser: AddressParser,
                  kwargs: dict[str, Any]) -> None:
        local_name: str = kwargs.pop('local_name', None)
        given_peers: Sequence[str] = kwargs.pop('peers', [])
        if local_name is None:
            raise ConfigError('The cluster instance needs a local name.')
        local_addr = address_parser.parse(local_name)
        resolved = cls._resolve_name(local_addr.host)
        local_ip = cls._find_local_ip(local_addr.host, local_addr.port)
        if local_ip not in resolved:
            raise TransientConfigError(
                f'Invalid local IP: {local_ip!r} not in {resolved!r}')
        resolved.remove(local_ip)
        if not resolved:
            raise TransientConfigError(
                f'Could not find peers: {local_addr.host}')
        resolved_peers = {str(Address(peer_ip, local_addr.port))
                          for peer_ip in resolved}
        kwargs['local_name'] = str(Address(local_ip, local_addr.port))
        kwargs['peers'] = list(resolved_peers | set(given_peers))

    @classmethod
    def _resolve_name(cls, hostname: str) -> set[str]:
        try:
            _, _, ipaddrlist = socket.gethostbyname_ex(hostname)
        except OSError as exc:
            raise TransientConfigError(f'Could not resolve name: {hostname}',
                                       wait_hint=10.0) from exc
        if not ipaddrlist:
            raise TransientConfigError(f'Name resolved empty: {hostname}')
        return set(ipaddrlist)

    @classmethod
    def _find_local_ip(cls, hostname: str, port: int) -> Optional[str]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        with closing(sock), suppress(OSError):
            sock.connect((hostname, port))
            sockname: tuple[str, int] = sock.getsockname()
            return sockname[0]
        return None


class UdpTransport(Transport[UdpConfig]):
    """Implements :class:`~swimprotocol.transport.Transport` using UDP, without
    `broadcast <https://en.wikipedia.org/wiki/Broadcast_address>`_.

    This transport assumes that the name of each cluster member is in
    ``host:port`` format, and that any cluster member can receive UDP packets
    from any other cluster member.

    Args:
        config: The cluster configuration object.

    """

    config_type = UdpConfig

    def __init__(self, config: UdpConfig) -> None:
        super().__init__(config)
        self.address_parser: Final = config.address_parser
        self.udp_pack: Final = UdpPack(config.signatures)
        self._local_address = self.address_parser.parse(config.local_name)

    @property
    def bind_host(self) -> str:
        """The local bind address used to open the UDP socket to receive
        packets.

        See Also:
            :func:`asyncio.loop.create_datagram_endpoint`

        """
        bind_host: Optional[str] = self.config.bind_host
        return bind_host or self._local_address.host

    @property
    def bind_port(self) -> int:
        """The local bind port used to open the UDP socket to receive packets.

        See Also:
            :func:`asyncio.loop.create_datagram_endpoint`

        """
        bind_port: Optional[int] = self.config.bind_port
        return bind_port or self._local_address.port

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
    def add_arguments(cls, name: str, parser: ArgumentParser, *,
                      prefix: str = '--udp') -> None:
        group = parser.add_argument_group(f'{name} options')
        group.add_argument(f'{prefix}-bind', metavar='INTERFACE',
                           dest='swim_udp_bind',
                           help='The bind IP address.')
        group.add_argument(f'{prefix}-host', metavar='NAME',
                           dest='swim_udp_host',
                           help='The default remote hostname.')
        group.add_argument(f'{prefix}-port', metavar='NUM', type=int,
                           dest='swim_udp_port',
                           help='The default port number.')
