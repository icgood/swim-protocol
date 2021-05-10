
from __future__ import annotations

import os
from abc import ABCMeta
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import final, TypeVar, Final, Any, Union, Optional

from .sign import Signatures

__all__ = ['ConfigT_co', 'ConfigError', 'TransientConfigError', 'BaseConfig']

#: Covariant type variable for :class:`BaseConfig` sub-classes.
ConfigT_co = TypeVar('ConfigT_co', bound='BaseConfig', covariant=True)


class ConfigError(Exception):
    """Raised when the configuration is insufficient or invalid for running a
    cluster, along with a human-readable message about what was wrong.

    """
    pass


class TransientConfigError(ConfigError):
    """Raised when a possibly-temporary failure has prevented configuration of
    the cluster. This exception is often chained with the cause, e.g.
    :exc:`OSError`. Importantly, this exception indicates that configuration of
    the cluster may succeed eventually if retried.

    Args:
        msg: The exception message.
        wait_hint: A suggested :func:`~asyncio.sleep` time before trying again.

    """

    def __init__(self, msg: Optional[str] = None, *,
                 wait_hint: float = 60.0) -> None:
        super().__init__(msg)
        self.wait_hint: Final = wait_hint


class BaseConfig(metaclass=ABCMeta):
    """Configure the cluster behavior and characteristics.
    :class:`~swimprotocol.transport.Transport` implementations should
    sub-class to add additional configuration.

    Args:
        secret: The shared secret for cluster packet signatures.
        local_name: The unique name of the local cluster member.
        local_metadata: The local cluster member metadata.
        peers: At least one name of another known node in the cluster.
        ping_interval: Time between :term:`ping` attempts to random cluster
            members.
        ping_timeout: Time to wait for an :term:`ack` after sending a
            :term:`ping`.
        ping_req_count: Number of nodes to send a :term:`ping-req` when a
            :term:`ping` fails.
        ping_req_timeout: Time to wait for an *ack* after sending a
            :term:`ping-req`.
        suspect_timeout: Time to wait after losing connectivity with a cluster
            member before marking it offline.
        sync_interval: Time between sync attempts to disseminate cluster
            changes.

    Raises:
        ConfigError: The given configuration was invalid.
        TransientConfigError: The configuration failed due to a failure that
            may not be permanent.

    """

    def __init__(self, *, secret: Union[None, str, bytes],
                 local_name: str,
                 local_metadata: Mapping[str, bytes],
                 peers: Sequence[str],
                 ping_interval: float = 1.0,
                 ping_timeout: float = 0.3,
                 ping_req_count: int = 1,
                 ping_req_timeout: float = 0.9,
                 suspect_timeout: float = 5.0,
                 sync_interval: float = 0.5) -> None:
        super().__init__()
        self._signatures = Signatures(secret)
        self.local_name: Final = local_name
        self.local_metadata: Final = local_metadata
        self.peers: Final = peers
        self.ping_interval: Final = ping_interval
        self.ping_timeout: Final = ping_timeout
        self.ping_req_count: Final = ping_req_count
        self.ping_req_timeout: Final = ping_req_timeout
        self.suspect_timeout: Final = suspect_timeout
        self.sync_interval: Final = sync_interval
        self._validate()

    def _validate(self) -> None:
        if not self.local_name:
            raise ConfigError('This cluster instance needs a local name.')
        elif not self.peers:
            raise ConfigError('At least one cluster peer name is required.')

    @property
    def signatures(self) -> Signatures:
        """Generates and verifies cluster packet signatures."""
        return self._signatures

    @classmethod
    def add_arguments(cls, parser: ArgumentParser, *,
                      prefix: str = '--') -> None:
        """Implementations (such as the :term:`demo`) may use this method to
        add command-line based configuration for the transport.

        Note:
            Arguments added should use *prefix* and explicitly provide a unique
            name, e.g.::

                parser.add_argument(f'{prefix}arg', dest='swim_arg', ...)

            This prevents collision with other argument names and allows custom
            *prefix* values without affecting the :class:`~argparse.Namespace`.

        Args:
            parser: The argument parser.
            prefix: The prefix for added arguments, which should start with
                ``--`` and end with ``-``, e.g. ``'--'`` or ``'--foo-'``.

        """
        group = parser.add_argument_group('swim options')
        group.add_argument(f'{prefix}metadata', dest='swim_metadata',
                           nargs=2, metavar=('KEY', 'VAL'),
                           default=[], action='append',
                           help='Metadata for this node.')
        group.add_argument(f'{prefix}secret', dest='swim_secret',
                           metavar='STRING',
                           help='The secret string used to verify messages.')
        group.add_argument(f'{prefix}name', dest='swim_name',
                           metavar='localname',
                           help='External name or address for this node.')
        group.add_argument(f'{prefix}peer', dest='swim_peers',
                           metavar='peername', action='append', default=[],
                           help='At least one name or address of '
                                'a known peer.')

    @classmethod
    def _get_env(cls, env_prefix: str, env: str) -> Optional[str]:
        env_file_val = os.getenv(f'{env_prefix}_{env}_FILE')
        if env_file_val is not None:
            env_path = Path(env_file_val).expanduser()
            try:
                with open(env_path, 'r') as env_file:
                    return env_file.read().rstrip('\r\n')
            except OSError:
                pass
        env_val = os.getenv(f'{env_prefix}_{env}')
        if env_val is not None:
            return env_val
        return None

    @classmethod
    def _get_env_list(cls, env_prefix: str, env: str) -> Sequence[str]:
        env_val = cls._get_env(env_prefix, env)
        if env_val:
            return env_val.split(',')
        else:
            return []

    @classmethod
    def parse_args(cls, args: Namespace, *, env_prefix: str = 'SWIM') \
            -> dict[str, Any]:
        """Parse the given :class:`~argparse.Namespace` into a dictionary of
        keyword arguments for the :class:`BaseConfig` constructor. Sub-classes
        should override this method to add additional keyword arguments as
        needed.

        Some keywords will default to environment variables if not given in
        *args*:

        ``SWIM_SECRET``, ``SWIM_SECRET_FILE`` [*]_
          The *secret* keyword argument.

        ``SWIM_NAME``
          The *local_name* keyword argument.

        ``SWIM_PEERS``
          The comma-separated *peers* keyword argument.

        .. [*] The value is read from the given file path.

        Args:
            args: The command-line arguments.
            env_prefix: Prefix for the environment variables.

        """
        secret = args.swim_secret or cls._get_env(env_prefix, 'SECRET')
        local_name = args.swim_name or cls._get_env(env_prefix, 'NAME')
        local_metadata = {key: val.encode('utf-8')
                          for key, val in args.swim_metadata}
        peers = args.swim_peers or cls._get_env_list(env_prefix, 'PEERS')
        return {'secret': secret,
                'local_name': local_name,
                'local_metadata': local_metadata,
                'peers': peers}

    @final
    @classmethod
    def from_args(cls: type[ConfigT_co], args: Namespace,
                  **overrides: Any) -> ConfigT_co:
        """Build and return a new cluster config object. This first calls
        :meth:`.parse_args` and then passes the results as keyword arguments
        to the constructor.

        Args:
            args: The command-line arguments.
            overrides: Keyword arguments to override.

        """
        kwargs = cls.parse_args(args)
        kwargs |= overrides
        return cls(**kwargs)
