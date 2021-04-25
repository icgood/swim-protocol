
from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, Generic, Final, Optional

from pkg_resources import iter_entry_points, DistributionNotFound

__all__ = ['Plugins']

TypeT = TypeVar('TypeT', bound='type')


class Plugins(Generic[TypeT]):
    """Allows a generic base type to be implemented using
    `plugins <https://setuptools.readthedocs.io/en/latest/pkg_resources.html>`_
    defined internally in ``setup.py`` or other Python libraries.

    Args:
        base: The base type to be implemented.
        group: The entry point group name.

    """

    def __init__(self, base: TypeT, group: str) -> None:
        super().__init__()
        self.base: Final = base
        self.group: Final = group
        self._failures: dict[str, DistributionNotFound] = {}
        self._loaded: Optional[dict[str, TypeT]] = None

    @property
    def loaded(self) -> Mapping[str, TypeT]:
        """A mapping of plugin name to the *base* implementation sub-class.
        Accessing this property will cause lazy-loading of all plugins, and
        plugins that failed to load will not appear.

        """
        loaded = self._loaded
        if loaded is None:
            self._loaded = loaded = self._load(self.group)
        return loaded

    def _load(self, group: str) -> dict[str, TypeT]:
        loaded = {}
        for entry_point in iter_entry_points(group):
            name = entry_point.name
            try:
                loaded_type = entry_point.load()
            except DistributionNotFound as exc:
                self._failures[name] = exc
            else:
                loaded[name] = loaded_type
        return loaded

    def choose(self, name: str) -> TypeT:
        """Given a plugin name, return the *base* implementation sub-class as
        loaded from the entry points.

        Args:
            name: The name of the plugin entry point.

        Raises:
            DistributionNotFound: The plugin failed to load due to missing
                dependencies.
            ValueError: The plugin name was not found.

        """
        loaded = self.loaded
        if name not in loaded:
            if name in self._failures:
                raise self._failures[name]
            else:
                msg = f'{name!r} is not a valid {self.group!r} plugin'
                raise ValueError(msg)
        return loaded[name]

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f'{cls_name}({self.base!r}, {self.group!r}'
