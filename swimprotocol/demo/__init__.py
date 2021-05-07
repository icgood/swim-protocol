"""Runs a single cluster member for demo purposes, displaying status and
metadata changes to all cluster members as they occur. On a random interval of
approximately 10 seconds, a metadata field "token" is updated on each cluster
member, and should be disseminated to all other members.

"""

from __future__ import annotations

import asyncio
import logging
import signal
from argparse import Namespace, ArgumentParser
from asyncio import CancelledError
from contextlib import suppress, AsyncExitStack

from .changes import change_metadata
from .log import run_logging
from .screen import run_screen
from ..config import BaseConfig, ConfigError
from ..members import Members
from ..transport import load_transport, Transport

__all__ = ['main']


def main() -> int:
    parser = ArgumentParser(description=__doc__)

    transport_type = load_transport()
    transport_type.config_type.add_arguments(parser)

    group = parser.add_argument_group('swim demo options')
    group.add_argument('-c', '--curses', action='store_true',
                       help='Enable the curses display.')
    group.add_argument('-i', '--token-interval', metavar='SECONDS',
                       type=float, default=10.0,
                       help='Cluster member token update interval.')

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
    transport = transport_type(config)
    members = Members(config)
    async with AsyncExitStack() as stack:
        stack.enter_context(suppress(CancelledError))
        worker = await stack.enter_async_context(transport.enter(members))
        if args.curses:
            await stack.enter_async_context(run_screen(members))
        else:
            stack.enter_context(run_logging(members))
        await stack.enter_async_context(change_metadata(
            members, args.token_interval))
        task = asyncio.create_task(worker.run())
        loop.add_signal_handler(signal.SIGINT, task.cancel)
        loop.add_signal_handler(signal.SIGTERM, task.cancel)
        await task
    return 0
