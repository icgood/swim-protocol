
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from grpclib.server import Server

from .client import GrpcClient
from .server import SwimServer
from ..config import Config
from ..transport import Transport
from ..types import Handlers

__all__ = ['GrpcTransport']


class GrpcTransport(Transport):

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config: Final = config
        self.args: Final = config.args
        self._client = GrpcClient(config)

    @property
    def client(self) -> GrpcClient:
        return self._client

    @property
    def bind_host(self) -> str:
        return self.args.bind or self.config.local_address.host

    @property
    def bind_port(self) -> int:
        return self.config.local_address.port

    @asynccontextmanager
    async def enter(self, handlers: Handlers) -> AsyncIterator[None]:
        swim_server = SwimServer(handlers)
        server = Server([swim_server])
        await server.start(self.bind_host, self.bind_port)
        yield
        server.close()
        await server.wait_closed()

    @classmethod
    def init(cls, config: Config) -> Transport:
        return cls(config)
