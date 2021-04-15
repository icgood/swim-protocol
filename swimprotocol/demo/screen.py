
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

    def _add_metadata(self, stdscr: Any, i: int, member: Member) -> None:
        metadata = member.metadata
        for key in sorted(metadata):
            stdscr.addstr(' ')
            stdscr.addstr(key)
            stdscr.addstr('=', curses.A_DIM)
            stdscr.addstr(metadata[key],
                          curses.color_pair(i+1) | curses.A_BOLD)

    def _render(self, stdscr: Any) -> None:
        members = sorted(self.members.all, key=lambda m: m.address)
        for i, member in enumerate(members):
            stdscr.move(i, 0)
            stdscr.addstr(f'{member.address}',
                          curses.color_pair(i+1) | curses.A_BOLD)
            stdscr.addstr(' is ')
            stdscr.addstr(member.status.name,
                          curses.color_pair(i+1) | curses.A_BOLD)
            if member.local:
                stdscr.addstr('<', curses.A_BOLD)
            stdscr.move(i, 27)
            stdscr.addstr(f' {member.modified}', curses.A_BOLD)
            stdscr.move(i, 35)
            self._add_metadata(stdscr, i, member)
        stdscr.move(curses.LINES - 1, curses.COLS - 17)
        stdscr.addstr('Clock: ')
        stdscr.addstr(f'{self.members.clock}', curses.A_BOLD)

    def main(self, stdscr: Any) -> None:
        curses.cbreak()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_BLUE, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_YELLOW, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)
        curses.init_pair(8, curses.COLOR_RED, -1)
        curses.curs_set(0)
        stdscr.clear()
        while not self.done.is_set():
            stdscr.clear()
            self._render(stdscr)
            stdscr.refresh()
            with self.ready:
                self.ready.wait(timeout=1.0)


def run_screen(members: Members) -> AsyncExitStack:
    exit_stack = AsyncExitStack()
    screen = Screen(members)
    exit_stack.callback(screen.cancel)
    exit_stack.enter_context(members.listener.on_update(screen.update))
    asyncio.create_task(asyncio.to_thread(wrapper, screen.main))
    return exit_stack
