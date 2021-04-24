
from __future__ import annotations

import asyncio
from asyncio import BaseTransport, Condition, DatagramProtocol, \
    DatagramTransport
from collections import deque
from typing import cast, Final, Optional

from .pack import UdpPack
from ..address import AddressParser
from ..members import Member
from ..packet import Packet
from ..worker import IO

__all__ = ['SwimProtocol']


class SwimProtocol(DatagramProtocol, IO):
    """Implements :class:`~asyncio.DatagramProtocol` and
    :class:`~swimprotocol.worker.IO` to send and receive UDP as SWIM protocol
    packets.

    """

    def __init__(self, address_parser: AddressParser,
                 udp_pack: UdpPack) -> None:
        super().__init__()
        self.address_parser: Final = address_parser
        self.udp_pack: Final = udp_pack
        self._transport: Optional[DatagramTransport] = None
        self._queue_lock = Condition()
        self._queue: deque[Packet] = deque()

    @property
    def transport(self) -> DatagramTransport:
        """The current :class:`~asyncio.DatagramTransport` object."""
        transport = self._transport
        assert transport is not None
        return transport

    def connection_made(self, transport: BaseTransport) -> None:
        """Called when the UDP socket is initialized.

        See Also:
            :meth:`asyncio.BaseProtocol.connection_made`

        """
        self._transport = cast(DatagramTransport, transport)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Called when data is received on the UDP socket.

        See Also:
            :meth:`asyncio.DatagramProtocol.datagram_received`

        """
        packet = self.udp_pack.unpack(data)
        if packet is None:
            return
        asyncio.create_task(self._push(packet))

    async def _push(self, packet: Packet) -> None:
        async with self._queue_lock:
            self._queue.append(packet)
            self._queue_lock.notify()

    async def recv(self) -> Packet:
        async with self._queue_lock:
            await self._queue_lock.wait()
            return self._queue.popleft()

    async def send(self, member: Member, packet: Packet) -> None:
        packet_data = self.udp_pack.pack(packet)
        address = self.address_parser.parse(member.name)
        self.transport.sendto(packet_data, (address.host, address.port))
