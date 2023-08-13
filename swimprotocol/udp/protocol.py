

from __future__ import annotations

import asyncio
from asyncio import Queue, Protocol, DatagramProtocol
from concurrent.futures import ThreadPoolExecutor
from typing import Final, Optional

from .pack import UdpPack
from ..packet import Packet
from ..tasks import TaskOwner

__all__ = ['BaseProtocol', 'UdpProtocol', 'TcpProtocol']


class BaseProtocol(TaskOwner):
    """Base class of :class:`UdpProtocol` and :class:`TcpProtocol`. Each will
    call :meth:`.handle_packet` upon receipt of a full packet.

    Args:
        thread_pool: A thread pool for CPU-heavy operations.

    """

    def __init__(self, thread_pool: ThreadPoolExecutor, udp_pack: UdpPack,
                 recv_queue: Queue[Packet]) -> None:
        super().__init__()
        self.thread_pool: Final = thread_pool
        self.udp_pack: Final = udp_pack
        self.recv_queue: Final = recv_queue

    async def handle_packet(self, data: bytes) -> None:
        """Parse the *data* into a packet and push it onto the worker
        :attr:`~swimprotocol.worker.Worker.recv_queue`.

        Args:
            data: The bytes representing a packet to be parsed by
                :class:`~swimprotocol.udp.pack.UdpPack`.

        """
        loop = asyncio.get_running_loop()
        packet = await loop.run_in_executor(
            self.thread_pool, self.udp_pack.unpack, data)
        if packet is None:
            return
        await self.recv_queue.put(packet)


class UdpProtocol(BaseProtocol, DatagramProtocol):
    """Implements :class:`~asyncio.DatagramProtocol` to receive SWIM protocol
    packets by UDP.

    Each packet received is passed directly to :meth:`.handle_packet`.

    """

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.run_subtask(self.handle_packet(data))


class TcpProtocol(BaseProtocol, Protocol):
    """Implements :class:`~asyncio.Protocol` to receive SWIM protocol packets
    by TCP.

    All data received is accumulated until the connection is closed, with the
    result treated as a complete packet and sent to :meth:`.handle_packet`.

    """

    def __init__(self, thread_pool: ThreadPoolExecutor, udp_pack: UdpPack,
                 recv_queue: Queue[Packet]) -> None:
        super().__init__(thread_pool, udp_pack, recv_queue)
        self._buf = bytearray()

    def data_received(self, data: bytes) -> None:
        self._buf += data

    def connection_lost(self, exc: Optional[Exception]) -> None:
        data = self._buf
        self._buf = bytearray()
        if exc is not None:
            return
        self.run_subtask(self.handle_packet(data))
