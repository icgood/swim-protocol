
from __future__ import annotations

from abc import abstractmethod, ABCMeta
from contextlib import AbstractAsyncContextManager
from typing import Generic, TypeVar, Final, ClassVar, Optional

from pkg_resources import iter_entry_points, DistributionNotFound

from .config import ConfigT_co, BaseConfig
from .members import Members
from .worker import Worker

__all__ = ['TransportT', 'load_transport', 'Transport']

#: Type variable for :class:`Transport` implementations.
TransportT = TypeVar('TransportT', bound='Transport[BaseConfig]')


def load_transport(name: str = 'udp', *, group: str = __name__) \
        -> type[Transport[BaseConfig]]:
    """Load and return the :class:`Transport` implementation by *name*.

    Args:
        name: The name of the transport entry point.
        group: The :mod:`pkg_resources` entry point group.

    Raises:
        DistributionNotFound: A dependency of the transport entry point was not
            able to be satisfied.
        KeyError: The given name did not exist in the entry point group.

    """
    last_exc: Optional[DistributionNotFound] = None
    for entry_point in iter_entry_points(group, name):
        try:
            transport_type: type[Transport[BaseConfig]] = entry_point.load()
        except DistributionNotFound as exc:
            last_exc = exc
        else:
            return transport_type
    if last_exc is not None:
        raise last_exc
    else:
        raise KeyError(f'{name!r} entry point not found in {group!r}')


class Transport(Generic[ConfigT_co], metaclass=ABCMeta):
    """Interface of the basic functionality needed to act as the
    :term:`transport` layer for the SWIM protocol. The transport layer is
    responsible for sending and receiving :term:`ping`, :term:`ping-req`, and
    :term:`ack` packets for failure detection, and transmitting :term:`gossip`
    for dissemination.

    Args:
        config: The cluster config object.

    """

    #: The :class:`~swimprotocol.config.BaseConfig` sub-class used by this
    #: transport.
    config_type: ClassVar[type[ConfigT_co]]

    def __init__(self, config: ConfigT_co) -> None:
        super().__init__()
        self.config: Final = config

    @abstractmethod
    def enter(self, members: Members) -> AbstractAsyncContextManager[Worker]:
        """Returns an async context manager that, when entered, provides a
        :class:`~swimprotocol.worker.Worker` instance that uses the transport
        for transmitting and receiving SWIM protocol packets.

        Args:
            members: Tracks the state of the cluster members.

        """
        ...
