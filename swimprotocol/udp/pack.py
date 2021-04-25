
from __future__ import annotations

import pickle
import struct
from typing import Final, Optional

from ..packet import Packet
from ..sign import Signatures

__all__ = ['UdpPack']

_prefix = struct.Struct('!BBH')


class UdpPack:
    """Packs and unpacks SWIM protocol :class:`~swimprotocol.packet.Packet`
    objects from raw UDP packets. The :mod:`pickle` module is used for
    serialization, so :class:`~swimprotocol.sign.Signatures` is used to sign
    the payloads.

    Args:
        signatures: Generates and verifies cluster packet signatures.
        pickle_protocol: The :mod:`pickle` protocol version number.
        prefix_xor: A 4-byte string used to XOR the packet prefix, as a sanity
            check to detect malformed or incomplete UDP packets.

    """

    def __init__(self, signatures: Signatures, *,
                 pickle_protocol: int = pickle.HIGHEST_PROTOCOL,
                 prefix_xor: bytes = b'SWIM') -> None:
        super().__init__()
        if len(prefix_xor) != _prefix.size:
            raise ValueError(f'{prefix_xor!r} must be {_prefix.size} bytes')
        self.signatures: Final = signatures
        self.pickle_protocol: Final = pickle_protocol
        self.prefix_xor: Final = prefix_xor

    def _xor_prefix(self, prefix: bytes) -> bytes:
        zipped = zip(prefix, self.prefix_xor)
        return bytes([left ^ right for left, right in zipped])

    def pack(self, packet: Packet) -> bytes:
        """Uses :mod:`pickle` to serialize *packet*, generates a digital
        signature of the pickled data, and returns a byte-string that can be
        sent as a raw UDP packet.

        The resulting byte-string starts with a 4-byte :mod:`struct` prefix
        (XOR'ed with *prefix_xor*) with the `struct format
        <https://docs.python.org/3/library/struct.html#format-strings>`_
        ``!BBH``. The first byte is the length of the salt, the second byte is
        the length of the signature, and the final two bytes are the length of
        the pickled payload. After the prefix, the salt, digest, and pickled
        payload byte-strings are concatenated.

        Args:
            packet: The SWIM protocol packet to serialize.

        """
        pickled = pickle.dumps(packet, self.pickle_protocol)
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
        """Deserializes a byte-string that was created using :meth:`.pack` into
        a SWIM protocol packet. If any assumptions about the serialized data
        are not met, including an invalid signature, ``None`` is returned to
        indicate that *data* was malformed or incomplete.

        Args:
            data: The serialized byte-string of the SWIM protocol packet.

        """
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
