
from __future__ import annotations

import asyncio
import random
import uuid
from contextlib import AsyncExitStack
from typing import NoReturn

from ..members import Members

__all__ = ['change_metadata']


async def _randomize_local(members: Members, interval: float) -> NoReturn:
    local = members.local
    assert local.metadata
    while True:
        new_token = uuid.uuid4().bytes
        new_metadata = dict(local.metadata) | {'token': new_token}
        members.update(local, new_metadata=new_metadata)
        sleep_sec = random.normalvariate(interval, interval / 5)
        await asyncio.sleep(sleep_sec)


def change_metadata(members: Members, interval: float) -> AsyncExitStack:
    exit_stack = AsyncExitStack()
    task = asyncio.create_task(_randomize_local(members, interval))
    exit_stack.callback(task.cancel)
    return exit_stack
