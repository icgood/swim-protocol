"""Runs a single cluster member for demo purposes, displaying status and
metadata changes to all cluster members as they occur. On a random interval of
approximately 10 seconds, a metadata field "token" is updated on each cluster
member, and should be disseminated to all other members.

"""

from __future__ import annotations

import sys
assert sys.platform != 'win32'

# ruff: noqa: E402

import asyncio
import logging
import signal
from argparse import Namespace, ArgumentParser
from asyncio import Event
from contextlib import AsyncExitStack

from .changes import change_metadata
from .screen import run_screen
from ..config import BaseConfig, ConfigError
from ..members import Members
from ..transport import load_transport, Transport
from ..worker import Worker

__all__ = ['main']


def main() -> int:
    parser = ArgumentParser(description=__doc__)

    transport_type = load_transport()
    transport_type.config_type.add_arguments(parser)

    group = parser.add_argument_group('swim demo options')
    group.add_argument('-i', '--token-interval', metavar='SECONDS',
                       type=float, help='Randomize metadata on an interval.')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)-15s %(name)s %(message)s')

    try:
        return asyncio.run(run(transport_type, args))
    except ConfigError as exc:
        parser.error(str(exc))


async def run(transport_type: type[Transport[BaseConfig]],
              args: Namespace) -> int:
    loop = asyncio.get_running_loop()
    config = transport_type.config_type.from_args(args)
    members = Members(config)
    worker = Worker(config, members)
    transport = transport_type(config, worker)
    done = Event()
    loop.add_signal_handler(signal.SIGINT, done.set)
    loop.add_signal_handler(signal.SIGTERM, done.set)
    async with AsyncExitStack() as stack:
        # stack.enter_context(suppress(CancelledError))
        await stack.enter_async_context(transport)
        await stack.enter_async_context(worker)
        await stack.enter_async_context(run_screen(members))
        await stack.enter_async_context(change_metadata(
            members, args.token_interval))
        await done.wait()
    return 0
