swim-protocol
=============

[SWIM protocol][0] implementation for exchanging cluster membership status and
metadata.

[![build](https://github.com/icgood/swim-protocol/actions/workflows/python-package.yml/badge.svg)](https://github.com/icgood/swim-protocol/actions/workflows/python-package.yml)
[![Coverage Status](https://coveralls.io/repos/github/icgood/swim-protocol/badge.svg?branch=main)](https://coveralls.io/github/icgood/swim-protocol?branch=main)
[![PyPI](https://img.shields.io/pypi/v/swim-protocol.svg)](https://pypi.python.org/pypi/swim-protocol)
[![PyPI](https://img.shields.io/pypi/pyversions/swim-protocol.svg)](https://pypi.python.org/pypi/swim-protocol)
[![PyPI](https://img.shields.io/pypi/l/swim-protocol.svg)](https://pypi.python.org/pypi/swim-protocol)

This library is intended to fit into an [asyncio][1] event loop to help
synchronize a distributed group of processes.

#### [Introduction](https://icgood.github.io/swim-protocol/intro.html)

#### [API Documentation](https://icgood.github.io/swim-protocol/)

## Install and Usage

```console
$ pip install swim-protocol
```

#### Running the Demo

There is a [demo][2] application included as a reference implementation. Try it
out by running the following, each from a new terminal window, and use _Ctrl-C_
to exit:

```console
$ swim-protocol-demo -c --name 127.0.0.1:2001 --peer 127.0.0.1:2003 --metadata name one
$ swim-protocol-demo -c --name 127.0.0.1:2002 --peer 127.0.0.1:2001 --metadata name two
$ swim-protocol-demo -c --name 127.0.0.1:2003 --peer 127.0.0.1:2001 --metadata name three
$ swim-protocol-demo -c --name 127.0.0.1:2004 --peer 127.0.0.1:2003 --metadata name four
```

Typing in any window will disseminate what has been typed across the cluster
with [eventual consistency][6].

![swim-protocol-demo](https://user-images.githubusercontent.com/438413/117895781-13f6b400-b28d-11eb-997d-d8b9dbc455cb.gif)

### Getting Started

First you should create a new [UdpConfig][100] object:

```python
from swimprotocol.udp import UdpConfig

config = UdpConfig(local_name='127.0.0.1:2001',
                   local_metadata={'name': b'one'},
                   peers=['127.0.0.1:2002'])
```

All other config arguments have default values, which are tuned somewhat
arbitrarily with a small cluster of 3-4 members in mind.

Now you can create the cluster members manager and transport layer, and enter
the event loop:

```python
from contextlib import AsyncExitStack
from swimprotocol.members import Members
from swimprotocol.udp import UdpTransport

transport = UdpTransport(config)
members = Members(config)
async with AsyncExitStack() as stack:
    worker = await stack.enter_async_context(transport.enter(members))
    await worker.run()  # or schedule as a task
```

These snippets demonstrate the UDP transport layer directly. For a more generic
approach that uses [argparse][11] and [load_transport][12], check out the
[demo][2].

If your application is deployed as a [Docker Service][13], the [UdpConfig][100]
`discovery=True` keyword argument can be used to discover configuration based
on the service name. See the [documentation][14] for more comprehensive usage.

### Checking Members

The [Members][101] object provides a few ways to check on the cluster and its
members:

```python
for member in members.non_local:
    # all other known cluster members
    print(member.name, member.status, member.metadata)

from swimprotocol.status import Status
for member in members.get_status(Status.AVAILABLE):
    # all cluster members except offline
    print(member.name, member.status, member.metadata)
```

Alternatively, listen for status or metadata changes on all members:

```python
from swimprotocol.member import Member

async def _updated(member: Member) -> None:
    print('updated:', member.name, member.status, member.metadata)

async with AsyncExitStack() as stack:
    # ...
    stack.enter_context(members.listener.on_notify(_updated))
```

### UDP Transport Security

The [UdpTransport][102] transport layer (the only included transport
implementation) uses salted [hmac][7] digests to sign each UDP packet payload.
Any UDP packets received that are malformed or have an invalid signature are
*silently* ignored. The eventual consistency model should recover from packet
loss.

The signatures rely on a [shared secret][8] between all cluster members, given
as the `secret=b'...'` argument to the [Config][100] constructor. If
`secret=None` is used, it defaults to [`uuid.getnode()`][9] but this is **not
secure** for production setups unless all sockets are bound to a local loopback
interface.

The cluster member metadata is **not** encrypted during transmission, so only
private networks should be used if metadata includes any secret data, or that
secret data should be encrypted separately by the application. Also be aware
that low [MTU][10] sizes on public networks may affect the ability to
synchronize larger amounts of metadata.

## Development

You will need to do some additional setup to develop and test plugins. Install
[Hatch][3] to use the CLI examples below.

Run all tests and linters:

```console
$ hatch run check
```

Because this project supports several versions of Python, you can use the
following to run the checks on all versions:

```console
$ hatch run all:check
```

### Type Hinting

This project makes heavy use of Python's [type hinting][4] system, with the
intention of a clean run of [mypy][5]:

```console
$ mypy
```

No code contribution will be accepted unless it makes every effort to use type
hinting to the extent possible and common in the rest of the codebase.

[0]: https://www.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf
[1]: https://docs.python.org/3/library/asyncio.html
[2]: https://github.com/icgood/swim-protocol/blob/main/swimprotocol/demo/__init__.py
[3]: https://hatch.pypa.io/latest/install/
[4]: https://docs.python.org/3/library/typing.html
[5]: http://mypy-lang.org/
[6]: https://en.wikipedia.org/wiki/Eventual_consistency
[7]: https://docs.python.org/3/library/hmac.html
[8]: https://en.wikipedia.org/wiki/Shared_secret
[9]: https://docs.python.org/3/library/uuid.html#uuid.getnode
[10]: https://en.wikipedia.org/wiki/Maximum_transmission_unit
[11]: https://docs.python.org/3/library/argparse.html
[12]: https://icgood.github.io/swim-protocol/swimprotocol.html#swimprotocol.transport.load_transport
[13]: https://docs.docker.com/engine/swarm/how-swarm-mode-works/services/
[14]: https://icgood.github.io/swim-protocol/swimprotocol.udp.html#docker-services

[100]: https://icgood.github.io/swim-protocol/swimprotocol.udp.html#swimprotocol.udp.UdpConfig
[101]: https://icgood.github.io/swim-protocol/swimprotocol.html#swimprotocol.members.Member
[102]: https://icgood.github.io/swim-protocol/swimprotocol.udp.html#swimprotocol.udp.UdpTransport
