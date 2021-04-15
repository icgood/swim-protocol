
from __future__ import annotations

import asyncio
import curses
from contextlib import AsyncExitStack
from curses import wrapper
from threading import Event, Condition
from typing import Final, Any

from ..members import Member, Members

__all__ = ['run_screen']


class Screen:

    def __init__(self, members: Members) -> None:
        super().__init__()
        self.members: Final = members
        self.ready: Final = Condition()
        self.done: Final = Event()

    async def update(self, updated: Member) -> None:
        with self.ready:
            self._updated = updated
            self.ready.notify()

    def cancel(self) -> None:
        self.done.set()
        with self.ready:
            self.ready.notify()

    def _render(self, stdscr: Any) -> None:
        members = sorted(self.members.all, key=lambda m: m.address)
        for i, member in enumerate(members):
            stdscr.addstr(i, 0, f'{member.address} is {member.status.name}')
            stdscr.addstr(i, 25, f' {member.metadata!r}')

    def main(self, stdscr: Any) -> None:
        curses.cbreak()
        stdscr.clear()
        while not self.done.is_set():
            stdscr.clear()
            self._render(stdscr)
            stdscr.refresh()
            with self.ready:
                self.ready.wait()


def run_screen(members: Members) -> AsyncExitStack:
    exit_stack = AsyncExitStack()
    screen = Screen(members)
    exit_stack.callback(screen.cancel)
    exit_stack.enter_context(members.listener.on_update(screen.update))
    asyncio.create_task(asyncio.to_thread(wrapper, screen.main))
    return exit_stack
