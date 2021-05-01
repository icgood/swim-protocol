
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from ..members import Member, Members

__all__ = ['run_logging']

logger = logging.getLogger(__name__)


async def update(member: Member) -> None:
    logger.info(f'{member.name} is {member.status.name}: {member.metadata!r}')


@contextmanager
def run_logging(members: Members) -> Iterator[None]:
    with members.listener.on_notify(update):
        yield
