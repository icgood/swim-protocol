"""SWIM protocol implementation for exchanging membership status and metadata.

"""

from __future__ import annotations

import asyncio
import logging
from argparse import Namespace, ArgumentParser, ArgumentDefaultsHelpFormatter

__all__ = ['main']


def main() -> int:
    parser = ArgumentParser(description=__doc__,
                            formatter_class=ArgumentDefaultsHelpFormatter)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.ERROR if args.quiet else logging.INFO,
        format='%(asctime)-15s %(name)s %(message)s')

    return asyncio.run(run(args))


async def run(args: Namespace) -> int:
    return 0


if __name__ == '__main__':
    raise RuntimeError('Use setuptools entry_points to execute')
