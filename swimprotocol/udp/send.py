
from __future__ import annotations

import asyncio
from asyncio import Queue, Protocol, DatagramTransport
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from typing import NoReturn

from .config import UdpConfig
from .pack import UdpPack
from ..address import Address
from ..members import Member
from ..packet import Packet
from ..tasks import DaemonTask

__all__ = ['UdpSend']


class UdpSend(DaemonTask):
    """Daemon task that waits for packets on *send_queue* and sends them using
    either by UDP or -- for oversized packets -- establishing a TCP connection.

    """

    def __init__(self, config: UdpConfig, udp_pack: UdpPack,
                 thread_pool: ThreadPoolExecutor,
                 send_queue: Queue[tuple[Member, Packet]],
                 udp_transport: DatagramTransport) -> None:
        super().__init__()
        self._address_parser = config.address_parser
        self._mtu_size = config.mtu_size
        self._udp_pack = udp_pack
        self._thread_pool = thread_pool
        self._send_queue = send_queue
        self._udp_transport = udp_transport

    async def run(self) -> NoReturn:
        send_queue = self._send_queue
        while True:
            member, packet = await send_queue.get()
            asyncio.create_task(self._do_send(member, packet))

    async def _do_send(self, member: Member, packet: Packet) -> None:
        thread_pool = self._thread_pool
        udp_transport = self._udp_transport
        loop = asyncio.get_running_loop()
        packet_data = await loop.run_in_executor(
            thread_pool, self._udp_pack.pack, packet)
        address = self._address_parser.parse(member.name)
        if len(packet_data) <= self._mtu_size:
            udp_transport.sendto(packet_data, (address.host, address.port))
        else:
            asyncio.create_task(self._tcp_send(packet_data, address))

    async def _tcp_send(self, packet_data: bytes, address: Address) -> None:
        loop = asyncio.get_running_loop()
        try:
            tcp_transport, _ = await loop.create_connection(
                Protocol, address.host, address.port)
            with closing(tcp_transport):
                tcp_transport.write(packet_data)
        except Exception:  # noqa: S110
            pass
