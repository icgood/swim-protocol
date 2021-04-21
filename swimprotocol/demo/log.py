
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from ..members import Member, Members

__all__ = ['run_logging']

logger = logging.getLogger(__name__)


async def update(updated: Member) -> None:
    logger.info(f'{updated.name} is {updated.status.name}:'
                f' {updated.metadata!r}')


@contextmanager
def run_logging(members: Members) -> Iterator[None]:
    with members.listener.on_update(update):
        yield
