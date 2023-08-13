"""Runs a cluster member.

Each member in the cluster has a sub-directory with its member name. Files
placed in the sub-directory of the local member will be synchronized to the
same sub-directory on other members of the cluster. Signal the process with
SIGHUP to detect file changes.

"""

from __future__ import annotations

import asyncio
import os
import os.path
import signal
import sys
from argparse import Namespace, ArgumentParser
from asyncio import CancelledError
from contextlib import suppress, AsyncExitStack
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile

from .config import BaseConfig, ConfigError
from .members import Members, Member
from .status import Status
from .transport import load_transport, Transport
from .worker import Worker

__all__ = ['main']

_statuses = [(Path('.online'), Status.ONLINE),
             (Path('.offline'), Status.OFFLINE),
             (Path('.suspect'), Status.SUSPECT),
             (Path('.available'), Status.AVAILABLE),
             (Path('.unavailable'), Status.UNAVAILABLE)]


def main() -> int:
    parser = ArgumentParser(description=__doc__)

    transport_type = load_transport()
    transport_type.config_type.add_arguments(parser)

    group = parser.add_argument_group('app options')
    group.add_argument('directory', type=Path, default='.')
    args = parser.parse_args()

    os.umask(0o022)
    base_path = Path(args.directory)
    base_path.mkdir(exist_ok=True)
    for sub_path, _ in _statuses:
        (base_path / sub_path).mkdir(exist_ok=True)

    try:
        return asyncio.run(run(transport_type, args, base_path))
    except ConfigError as exc:
        parser.error(str(exc))


async def run(transport_type: type[Transport[BaseConfig]],
              args: Namespace, base_path: Path) -> int:
    loop = asyncio.get_running_loop()
    config = transport_type.config_type.from_args(args)
    transport = transport_type(config)
    members = Members(config)
    worker = Worker(config, members)
    read_local = partial(_read_local, base_path, members)
    write_member = partial(_write_member, base_path)
    read_local()
    async with AsyncExitStack() as stack:
        stack.enter_context(suppress(CancelledError))
        await stack.enter_async_context(transport.enter(worker))
        stack.enter_context(members.listener.on_notify(write_member))
        task = asyncio.create_task(worker.run())
        if sys.platform != 'win32':
            loop.add_signal_handler(signal.SIGHUP, read_local)
        loop.add_signal_handler(signal.SIGINT, task.cancel)
        loop.add_signal_handler(signal.SIGTERM, task.cancel)
        await task
    _cleanup(base_path, members)
    return 0


def _try_link(from_path: Path, to_path: Path) -> bool:
    rel_path = os.path.relpath(from_path.parent.absolute(),
                               to_path.parent.absolute())
    link_path = Path(rel_path) / from_path.name
    try:
        os.symlink(link_path, to_path)
    except FileExistsError:
        return False
    else:
        return True


def _try_unlink(path: Path) -> bool:
    try:
        os.unlink(path)
    except FileNotFoundError:
        return False
    else:
        return True


def _update_status(from_path: Path, status_path: Path, name: str,
                   has_status: object) -> None:
    to_path = status_path / name
    if has_status:
        if _try_link(from_path, to_path):
            status_path.touch()
    else:
        if _try_unlink(to_path):
            status_path.touch()


def _read_local(base_path: Path, members: Members) -> None:
    local_member = members.local
    local_path = base_path / local_member.name
    local_path.mkdir(exist_ok=True)
    _try_link(local_path, base_path / '.local')
    local_metadata: dict[str, bytes] = {}
    for sub_path in local_path.iterdir():
        local_metadata[sub_path.name] = sub_path.read_bytes()
    members.update(local_member, new_metadata=local_metadata)


async def _write_member(base_path: Path, member: Member) -> None:
    if member.local:
        return
    member_path = base_path / member.name
    member_path.mkdir(exist_ok=True)
    for sub_path, status in _statuses:
        _update_status(member_path, base_path / sub_path, member.name,
                       member.status & status)
    existing_names = set(f.name for f in member_path.iterdir())
    removed_names = existing_names - member.metadata.keys()
    for name in removed_names:
        _try_unlink(member_path / name)
    for name, val in member.metadata.items():
        with NamedTemporaryFile(delete=False) as tmp:
            tmp.write(val)
        os.rename(tmp.name, member_path / name)
    member_path.touch()
    hook_path = base_path / 'on-update'
    if hook_path.is_file():
        hook = await asyncio.create_subprocess_exec(
            hook_path,
            member.name,
            member.status.name,
            member_path.absolute())
        await hook.communicate()


def _cleanup(base_path: Path, members: Members) -> None:
    os.unlink(base_path / '.local')
    for member in members.non_local:
        member_path = base_path / member.name
        for sub_path in member_path.iterdir():
            os.unlink(sub_path)
    for sub_path, _ in _statuses:
        status_path = base_path / sub_path
        for status_sub_path in status_path.iterdir():
            os.unlink(status_sub_path)
