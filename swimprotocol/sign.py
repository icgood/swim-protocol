
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from typing import Final, Union

from . import __version__

__all__ = ['Signatures']

_SigTuple = tuple[bytes, bytes]


class Signatures:

    def __init__(self, secret: Union[None, str, bytes], *,
                 hash_name: str = 'sha256',
                 salt_len: int = 16,
                 check_version: bool = True) -> None:
        super().__init__()
        if secret is None:
            secret = b'%x' % uuid.getnode()
        elif isinstance(secret, str):
            secret = secret.encode('utf-8')
        self.secret: Final = secret
        self.hash_name: Final = hash_name
        self.salt_len: Final = salt_len
        self.digest_size: Final = hashlib.new(hash_name).digest_size
        self.version = __version__.encode('ascii') if check_version else b''

    def sign(self, data: bytes) -> _SigTuple:
        salt = secrets.token_bytes(16)
        salted_data = b'%s%s%s' % (self.version, salt, data)
        digest = hmac.digest(self.secret, salted_data, self.hash_name)
        return salt, digest

    def verify(self, data: bytes, sig: _SigTuple) -> bool:
        salt, sig_digest = sig
        salted_data = b'%s%s%s' % (self.version, salt, data)
        digest = hmac.digest(self.secret, salted_data, self.hash_name)
        return hmac.compare_digest(sig_digest, digest)
