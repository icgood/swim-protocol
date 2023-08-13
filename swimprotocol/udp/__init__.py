
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, AsyncExitStack
from typing import Any, Final, Optional

from .config import UdpConfig
from .pack import UdpPack
from .protocol import UdpProtocol, TcpProtocol
from .send import UdpSend
from ..transport import Transport
from ..worker import Worker

__all__ = ['UdpTransport']


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

    def __init__(self, config: UdpConfig, worker: Worker) -> None:
        super().__init__(config, worker)
        self.address_parser: Final = config.address_parser
        self.udp_pack: Final = UdpPack(config.signatures)
        self._local_address = self.address_parser.parse(config.local_name)
        self._stack = AsyncExitStack()

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

    async def __aenter__(self) -> None:
        loop = asyncio.get_running_loop()
        stack = self._stack
        thread_pool = stack.enter_context(ThreadPoolExecutor())
        recv_queue = self.worker.recv_queue
        send_queue = self.worker.send_queue
        tcp_server = await loop.create_server(
            lambda: TcpProtocol(thread_pool, self.udp_pack, recv_queue),
            self.bind_host, self.bind_port, reuse_port=True)
        udp_transport, _ = await loop.create_datagram_endpoint(
            lambda: UdpProtocol(thread_pool, self.udp_pack, recv_queue),
            reuse_port=True, local_addr=(self.bind_host, self.bind_port))
        await stack.enter_async_context(UdpSend(
            self.config, self.udp_pack, thread_pool, send_queue,
            udp_transport))
        stack.enter_context(closing(udp_transport))
        await stack.enter_async_context(tcp_server)

    def __aexit__(self, *exc_details: Any) -> Any:
        return self._stack.__aexit__(*exc_details)
