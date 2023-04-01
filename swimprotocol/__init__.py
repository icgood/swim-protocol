
from __future__ import annotations

from importlib.metadata import distribution

__all__ = ['__version__']

#: The package version string.
#:
#: See Also:
#:    `PEP 396 <https://www.python.org/dev/peps/pep-0396/>`_
__version__: str = distribution('swim-protocol').version
