
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
    """Interface of the basic functionality needed to act as the
    :term:`transport` layer for the SWIM protocol. The transport layer is
    responsible for sending and receiving :term:`ping`, :term:`ping-req`, and
    :term:`ack` packets for failure detection, and transmitting :term:`gossip`
    for dissemination.

    """

    @classmethod
    @abstractmethod
    def add_arguments(cls, name: str, parser: ArgumentParser) -> None:
        """Additional configuration needed by the transport may be added to the
        current argument *parser*.

        Args:
            name: The name of the transport plugin.
            parser: The argument parser.

        """
        ...

    @classmethod
    @abstractmethod
    def init(cls, config: Config) -> Transport:
        """Initializes the :class:`Transport` and returns a new instance
        given the *config*. Any arguments added by :meth:`.add_arguments` can
        be accessed on ``config.args``.

        Args:
            config: The cluster configuration object.

        """
        ...

    @abstractmethod
    def enter(self, members: Members) -> AbstractAsyncContextManager[Worker]:
        """Returns an async context manager that, when entered, provides a
        :class:`~swimprotocol.worker.Worker` instance that uses the transport
        for transmitting and receiving SWIM protocol packets.

        Args:
            members: Tracks the state of the cluster members.

        """
        ...


#: Manages the loading and access of :class:`Transport` implementations.
transport_plugins = Plugins(Transport, __name__)
