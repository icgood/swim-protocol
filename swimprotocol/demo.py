"""

"""

from __future__ import annotations

import asyncio
import logging
import signal
from argparse import Namespace, ArgumentParser
from asyncio import CancelledError
from contextlib import suppress, AsyncExitStack
from ipaddress import ip_address

from grpclib.server import Server

from . import Address
from .config import Config
from .members import Members
from .server import SwimServer

__all__ = ['main']


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-b', '--bind', metavar='INTERFACE', type=ip_address,
                        help='The bind IP address, instead of HOST.')
    parser.add_argument('-m', '--metadata', nargs=2, metavar=('KEY', 'VAL'),
                        default=[], action='append',
                        help='Metadata for this node.')
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
    config = Config(args)
    members = Members(config, args.peers)
    service = SwimServer(config, members)
    server = Server([service])
    bind_host = args.bind or config.local_address.host
    bind_port = config.local_address.port
    async with AsyncExitStack() as stack:
        stack.enter_context(suppress(CancelledError))
        await server.start(bind_host, bind_port)
        forever = asyncio.gather(*[server.wait_closed(), service.start()])
        loop.add_signal_handler(signal.SIGINT, forever.cancel)
        loop.add_signal_handler(signal.SIGTERM, forever.cancel)
        await forever
    return 0
