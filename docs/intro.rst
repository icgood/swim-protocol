
=================
SWIM Introduction
=================

Goals
-----

This project is intended to implement the `SWIM`_ white paper, with elements
drawn from `Serf`_ as well. The goals are simple:

- Each :term:`member` in a cluster should be *eventually* aware of all other
  nodes in the cluster, and is able to run code when a node's :term:`status`
  changes.
- Each :term:`member` may define a set of key/value strings as its
  :term:`metadata`. All members are *eventually* aware of all other members'
  metadata, as well as any changes.

Failure Detection
~~~~~~~~~~~~~~~~~

The :term:`local member` chooses a remote :term:`member` at random and sent a
:term:`ping`. If the remote member does not respond with an :term:`ack` within
a timeout, at least one other remote :term:`member` is chosen and sent a
:term:`ping-req`. If the remote member *still* does not respond with an
:term:`ack`, it is declared :term:`suspect`. This process repeats indefinitely
across every member of the cluster. If ever a :term:`suspect` or
:term:`offline` member responds with an :term:`ack` via either a :term:`ping`
or a :term:`ping-req`, it is immediately returned to :term:`online` status.

Dissemination
~~~~~~~~~~~~~

The :term:`local member` chooses a remote :term:`member` at random to send
:term:`gossip`. The last known :term:`sequence clock` of the remote member is
used to determine what other :term:`members <member>` to gossip about.  For
example, if member **A** wanted to gossip about member **B** to member **C**,
and member **C** last reported a sequence clock of *9*, while **B** was last
updated at sequence clock *13*, then **A** would send the gossip. **C** would
then report a new sequence clock of *13* (or higher!) and future gossip about
**B** would not be sent. This process repeats indefinitely across every member
of the cluster. At rest, where all members have received the most recent gossip
about all other members, no gossip is sent at all until the next time a
:term:`member` changes :term:`status` or :term:`metadata`.

Glossary
--------

.. glossary::

   SWIM
      Scalable Weakly-consistent Infection-style Process Group Membership
      Protocol, defined in the `SWIM`_ white paper.

   member
   node
      A member is an instance that is initially aware of at least one other
      member, and then transitively is made aware of other members that are
      known by that member, forming a cluster.

   local member
      The :term:`member` corresponding to the current process. This
      :term:`member` is *always* online and is the only :term:`member` whose
      :term:`metadata` may be changed. The local member perceives other members
      in the cluster based on their most recently known :term:`status` and
      :term:`metadata`.

   status
      One of three states that a remote :term:`member` can hold, as perceived
      the :term:`local member`: :term:`online`, :term:`suspect`, or
      :term:`offline`.

   online : status
      A :term:`status` meaning recent failure detection attempts have
      successfully received an :term:`ack` from the remote :term:`member`.

   suspect : status
      A :term:`status` meaning that a recently-online :term:`member` has not
      responded to at least one failure detection attempt.

   offline : status
      A :term:`status` meaning the :term:`member` has not responded with an
      :term:`ack` to any recent failure detection attempts. A :term:`suspect`
      member becomes :term:`offline` only after some time elapses, to prevent
      false positives.

   metadata
      An immutable mapping of key/value strings associated with each
      :term:`member`. New mappings may be assigned, and the latest mapping will
      always be disseminated across the cluster.

   transport
      An interface for implementing alternative transmission mechanisms instead
      of the builtin :mod:`~swimprotocol.udp`. A transport is capable of
      sending and receiving :term:`packet` messages.

   packet
      A simple, one-way message that is sent from the :term:`member` to
      another. In :mod:`~swimprotocol.udp`, these directly correspond to
      `datagrams <https://en.wikipedia.org/wiki/Datagram>`_.

   ping : packet
      A :term:`packet` that requests that a remote :term:`member` reply to the
      source :term:`member` with an :term:`ack`. This is the most basic attempt
      to detect when members have gone offline.

   ping-req : packet
      A :term:`packet` that requests that a remote :term:`member` send its own
      :term:`ping` to a second remote :term:`member`. If the recipient receives
      an :term:`ack`, it is forwarded back to the source :term:`member`.

   ack : packet
      A :term:`packet` sent in response to a :term:`ping` or :term:`ping-req`
      indicating that the source :term:`member` is :term:`online`.

   gossip : packet
      A :term:`packet` that informs one :term:`member` of the currently
      known :term:`status` and :term:`metadata` of another :term:`member`.

   sequence clock
      A `Lamport timestamp`_, an always-increasing counter where the next value
      is always higher than any other observed value, used to determine whether
      :term:`gossip` is new enough to be applied or disseminated.

   demo
      The included `demo`_ is designed to randomize metadata changes on an
      interval to see them disseminated across the cluster, as well as watch as
      :term:`member` statuses change as demo instances are stopped and started.

.. _SWIM: https://www.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf
.. _Serf: https://www.serf.io/docs/internals/gossip.html
.. _Lamport timestamp: https://en.wikipedia.org/wiki/Lamport_timestamp
.. _demo: https://github.com/icgood/swim-protocol#running-the-demo
