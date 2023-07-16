
``swimprotocol.udp``
====================

.. automodule:: swimprotocol.udp

Docker Services
---------------

If your application is deployed as a `Docker Service`_, the
:class:`~swimprotocol.udp.UdpConfig` ``discovery=True`` keyword argument can be
used to discover configuration based on the service name. For example::

    config = UdpConfig(local_name='tasks.my-service:9999', discovery=True, ...)

Docker provides a `tasks`_ DNS lookup that resolves to the IP addresses of all
replicas of the service. In this example, ``tasks.my-service`` is resolved to
these IP addresses. The IP address local to the container is chosen as the
:term:`local member` and the rest are :term:`peer members <peer member>`.

In practice, this DNS lookup is often not immediately successful when the
replicas start up. A service may also be scaled down to a single replica, which
has no need of a cluster. These scenarios will raise a
:exc:`~swimprotocol.config.TransientConfigError` with a *wait_hint* value. This
exception can be caught to continuously retry the cluster configuration until
successful::

    async def start() -> None:
        while True:
            try:
                config = UdpConfig(local_name='tasks.my-service:9999',
                                   discovery=True, ...)
            except TransientConfigError as exc:
                await asyncio.sleep(exc.wait_hint)
            else:
                break
        # ...

.. _Docker Service: https://docs.docker.com/engine/swarm/how-swarm-mode-works/services/
.. _tasks: https://docs.docker.com/network/overlay/#container-discovery

``swimprotocol.udp.pack``
-------------------------

.. automodule:: swimprotocol.udp.pack

``swimprotocol.udp.protocol``
-----------------------------

.. automodule:: swimprotocol.udp.protocol
