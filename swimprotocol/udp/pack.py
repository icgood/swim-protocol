
from __future__ import annotations

import pickle
import struct
from typing import Final, Optional

from ..packet import Packet
from ..sign import Signatures

__all__ = ['UdpPack']

_prefix = struct.Struct('!BBH')


class UdpPack:

    def __init__(self, signatures: Signatures, *,
                 prefix_xor: bytes = b'SWIM') -> None:
        super().__init__()
        if len(prefix_xor) != _prefix.size:
            raise ValueError(f'{prefix_xor!r} must be {_prefix.size} bytes')
        self.signatures: Final = signatures
        self.prefix_xor: Final = prefix_xor

    def _xor_prefix(self, prefix: bytes) -> bytes:
        zipped = zip(prefix, self.prefix_xor)
        return bytes([left ^ right for left, right in zipped])

    def pack(self, packet: Packet) -> bytes:
        pickled = pickle.dumps(packet)
        salt, digest = self.signatures.sign(pickled)
        salt_start = _prefix.size
        digest_start = salt_start + len(salt)
        data_start = digest_start + len(digest)
        prefix = _prefix.pack(len(salt), len(digest), len(pickled))
        packed = bytearray(data_start + len(pickled))
        packed[0:salt_start] = self._xor_prefix(prefix)
        packed[salt_start:digest_start] = salt
        packed[digest_start:data_start] = digest
        packed[data_start:] = pickled
        return packed

    def unpack(self, data: bytes) -> Optional[Packet]:
        data_view = memoryview(data)
        salt_start = _prefix.size
        prefix = self._xor_prefix(data_view[0:salt_start])
        try:
            salt_len, digest_len, data_len = _prefix.unpack(prefix)
        except struct.error:
            return None
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
