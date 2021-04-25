
from __future__ import annotations

import pkg_resources

__all__ = ['__version__']

#: The package version string.
#:
#: See Also:
#:    `PEP 396 <https://www.python.org/dev/peps/pep-0396/>`_
__version__: str = pkg_resources.require('swim-protocol')[0].version
