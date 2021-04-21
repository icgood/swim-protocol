
from __future__ import annotations

import pickle
import struct
from typing import Final, Optional

from ..packet import Packet
from ..sign import Signatures

__all__ = ['UdpPack']

MAGIC_PREFIX = b'SWIM'
_prefix = struct.Struct('!4sBBH')


class UdpPack:

    def __init__(self, signatures: Signatures) -> None:
        super().__init__()
        self.signatures: Final = signatures

    def pack(self, packet: Packet) -> bytes:
        pickled = pickle.dumps(packet)
        salt, digest = self.signatures.sign(pickled)
        salt_start = _prefix.size
        digest_start = salt_start + len(salt)
        data_start = digest_start + len(digest)
        packed = bytearray(data_start + len(pickled))
        _prefix.pack_into(packed, 0, MAGIC_PREFIX,
                          len(salt), len(digest), len(pickled))
        packed[salt_start:digest_start] = salt
        packed[digest_start:data_start] = digest
        packed[data_start:] = pickled
        return packed

    def unpack(self, data: bytes) -> Optional[Packet]:
        data_view = memoryview(data)
        try:
            magic_prefix, salt_len, digest_len, data_len = \
                _prefix.unpack_from(data_view)
        except struct.error:
            return None
        if magic_prefix != MAGIC_PREFIX:
            return None
        salt_start = _prefix.size
        digest_start = salt_start + salt_len
        data_start = digest_start + digest_len
        data_end = data_start + data_len
        salt = data_view[salt_start:digest_start]
        digest = data_view[digest_start:data_start]
        pickled = data_view[data_start:data_end]
        signatures = self.signatures
        if len(digest) != signatures.digest_size or len(pickled) != data_len:
            return None
        if signatures.verify(pickled, (salt, digest)):
            packet = pickle.loads(pickled)
            assert isinstance(packet, Packet)
            return packet
        else:
            return None
