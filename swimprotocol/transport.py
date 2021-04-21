
from __future__ import annotations

from abc import abstractmethod
from argparse import ArgumentParser
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from .config import Config
from .members import Members
from .plugin import Plugins
from .worker import Worker

__all__ = ['Transport', 'transport_plugins']


class Transport(Protocol):

    @classmethod
    @abstractmethod
    def add_arguments(cls, name: str, parser: ArgumentParser) -> None:
        ...

    @classmethod
    @abstractmethod
    def init(cls, config: Config) -> Transport:
        ...

    @abstractmethod
    def enter(self, members: Members) -> AbstractAsyncContextManager[Worker]:
        ...


transport_plugins = Plugins(Transport, __name__)
