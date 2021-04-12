"""

"""

from __future__ import annotations

import asyncio
import logging
import signal
from argparse import Namespace, ArgumentParser
from asyncio import CancelledError
from contextlib import suppress, AsyncExitStack

from .members import Members
from .transport import load_transport
from .types import Address
from .worker import Worker

__all__ = ['main']


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-b', '--bind', metavar='INTERFACE',
                        help='The bind IP address, instead of HOST.')
    parser.add_argument('-m', '--metadata', nargs=2, metavar=('KEY', 'VAL'),
                        default=[], action='append',
                        help='Metadata for this node.')
    parser.add_argument('-t', '--transport', metavar='NAME',
                        help='The transport plugin name.')
    parser.add_argument('local', metavar='local-addr', type=Address.parse,
                        help='External connection address for this node.')
    parser.add_argument('peers', metavar='peer-addr',
                        type=Address.parse, nargs='+',
                        help='External connection address for peers.')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)-15s %(name)s %(message)s')

    return asyncio.run(run(args))


async def run(args: Namespace) -> int:
    loop = asyncio.get_running_loop()
    transport = load_transport(args)
    members = Members(transport.config, args.peers)
    worker = Worker(transport.config, members, transport.client)
    async with AsyncExitStack() as stack:
        stack.enter_context(suppress(CancelledError))
        await stack.enter_async_context(transport.enter(worker))
        task = await worker.start()
        loop.add_signal_handler(signal.SIGINT, task.cancel)
        loop.add_signal_handler(signal.SIGTERM, task.cancel)
        await task
    return 0