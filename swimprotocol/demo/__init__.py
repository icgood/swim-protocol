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
from ..config import Config
from ..members import Members
from ..transport import transport_plugins

__all__ = ['main']


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-m', '--metadata', nargs=2, metavar=('KEY', 'VAL'),
                        default=[], action='append', type=_utf8,
                        help='Metadata for this node.')
    parser.add_argument('-t', '--transport', metavar='NAME', default='udp',
                        help='The transport plugin name.')
    parser.add_argument('-s', '--secret', metavar='STRING',
                        help='The secret string used to verify messages.')
    parser.add_argument('-c', '--curses', action='store_true',
                        help='Enable the curses display.')
    parser.add_argument('-i', '--token-interval', type=float, default=10.0,
                        help='Cluster member token update interval.')
    parser.add_argument('local', metavar='localname',
                        help='External name or address for this node.')
    parser.add_argument('peers', metavar='peername', nargs='+',
                        help='At least one name or address of a known peer.')
    parser.set_defaults(config_type=Config)

    for transport_name, transport_type in transport_plugins.loaded.items():
        transport_type.add_arguments(transport_name, parser)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)-15s %(name)s %(message)s')

    return asyncio.run(run(args))


def _utf8(val: str) -> bytes:
    return val.encode('utf-8')


async def run(args: Namespace) -> int:
    loop = asyncio.get_running_loop()
    config: Config = args.config_type.from_args(args)
    transport = transport_plugins.choose(args.transport).init(config)
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
