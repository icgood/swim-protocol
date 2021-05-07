
from __future__ import annotations

import asyncio
import curses
from contextlib import AsyncExitStack
from curses import wrapper
from threading import Event, Condition
from typing import Final, Any

from ..members import Member, Members
from ..status import Status

__all__ = ['run_screen']


class Screen:

    def __init__(self, members: Members) -> None:
        super().__init__()
        self.members: Final = members
        self.ready: Final = Condition()
        self.done: Final = Event()

    async def update(self, updated: Member) -> None:
        with self.ready:
            self.ready.notify()

    def cancel(self) -> None:
        self.done.set()
        with self.ready:
            self.ready.notify()

    def _decode(self, val: bytes) -> str:
        try:
            return val.decode('utf-8')
        except UnicodeDecodeError:
            return val.hex()

    def _add_metadata(self, stdscr: Any, i: int, member: Member) -> None:
        metadata = member.metadata or {}
        if member.metadata is Member.METADATA_UNKNOWN:
            stdscr.addstr(' unknown', curses.A_BOLD)
            return
        for key in sorted(metadata):
            val_str = self._decode(metadata[key])
            stdscr.addstr(' ')
            stdscr.addstr(key)
            stdscr.addstr('=', curses.A_DIM)
            stdscr.addstr(val_str, curses.color_pair(i+1) | curses.A_BOLD)

    def _render(self, stdscr: Any) -> None:
        members = sorted(self.members)
        for i, member in enumerate(members):
            stdscr.move(i, 4)
            stdscr.addstr(member.name, curses.color_pair(i+1) | curses.A_BOLD)
            stdscr.addstr(' is ')
            stdscr.addstr(member.status.name,
                          curses.color_pair(i+1) | curses.A_BOLD)
            stdscr.move(i, 30)
            stdscr.addstr(f' {member.clock}', curses.A_BOLD)
            stdscr.move(i, 38)
            self._add_metadata(stdscr, i, member)
            if member.local:
                stdscr.move(i, 0)
                stdscr.addstr('>>> ', curses.A_BOLD)
                stdscr.move(i, curses.COLS - 4)
                stdscr.addstr(' <<<', curses.A_BOLD)
        stdscr.move(curses.LINES - 1, curses.COLS - 18)
        stdscr.addstr(' Available: ')
        available = len(self.members.get_status(Status.AVAILABLE)) + 1
        stdscr.addstr(f'{available}', curses.A_BOLD)

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

    async def run_thread(self) -> None:
        await asyncio.to_thread(wrapper, self.main)


def run_screen(members: Members) -> AsyncExitStack:
    exit_stack = AsyncExitStack()
    screen = Screen(members)
    main_task = asyncio.create_task(screen.run_thread())
    exit_stack.push_async_callback(asyncio.wait_for, main_task, None)
    exit_stack.enter_context(members.listener.on_notify(screen.update))
    exit_stack.callback(screen.cancel)
    return exit_stack
