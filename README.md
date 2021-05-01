swim-protocol
=============

[SWIM protocol][0] implementation for exchanging cluster membership status and
metadata.

[![Build Status](https://travis-ci.com/icgood/swim-protocol.svg?branch=main)](https://travis-ci.com/icgood/swim-protocol)
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

There is a [demo][2] application included as a reference implementation. Try it
out by running the following, each from a new terminal window, and use _Ctrl-C_
to exit:

```console
$ swim-protocol-demo -c -m name one 127.0.0.1:2001 127.0.0.1:2003
$ swim-protocol-demo -c -m name two 127.0.0.1:2002 127.0.0.1:2001
$ swim-protocol-demo -c -m name three 127.0.0.1:2003 127.0.0.1:2001
$ swim-protocol-demo -c -m name four 127.0.0.1:2004 127.0.0.1:2003
```

Every 10 seconds or so, each member will randomize its `token` metadata field,
which should be disseminated across the cluster with [eventual consistency][6].

### Getting Started

First you should create a new [Config][100] object:

```python
from argparse import ArgumentParser
from swimprotocol.config import Config

parser = ArgumentParser(...)
args = parser.parse_args()
config = Config(args, secret=b'...',
                local_name='127.0.0.1:2001',
                local_metadata={b'name': b'one'},
                peers=['127.0.0.1:2002'])
```

All other config arguments have default values, which are tuned somewhat
arbitrarily with a small cluster of 3-4 members in mind.

Now you can create the cluster members manager and transport layer, and enter
the event loop:

```python
from contextlib import AsyncExitStack
from swimprotocol.transport import transport_plugins
from swimprotocol.members import Members

transport = transport_plugins.choose('udp').init(config)
members = Members(config)
async with AsyncExitStack() as stack:
    worker = await stack.enter_async_context(transport.enter(members))
    await worker.run()  # or schedule as a task
```

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

async def _on_updated(member: Member) -> None:
    print('updated:', member.name, member.status, member.metadata)

async with AsyncExitStack() as stack:
    # ...
    stack.enter_context(members.listener.on_notify(_on_updated))
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

First off, I suggest activating a [venv][3]. Then, install the development
requirements and a local link to the *swim-protocol* package:

```
$ pip install -r requirements-dev.txt
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
[3]: https://docs.python.org/3/library/venv.html
[4]: https://docs.python.org/3/library/typing.html
[5]: http://mypy-lang.org/
[6]: https://en.wikipedia.org/wiki/Eventual_consistency
[7]: https://docs.python.org/3/library/hmac.html
[8]: https://en.wikipedia.org/wiki/Shared_secret
[9]: https://docs.python.org/3/library/uuid.html#uuid.getnode
[10]: https://en.wikipedia.org/wiki/Maximum_transmission_unit

[100]: https://icgood.github.io/swim-protocol/swimprotocol.html#swimprotocol.config.Config
[101]: https://icgood.github.io/swim-protocol/swimprotocol.html#swimprotocol.members.Member
[102]: https://icgood.github.io/swim-protocol/swimprotocol.udp.html#swimprotocol.udp.UdpTransport
