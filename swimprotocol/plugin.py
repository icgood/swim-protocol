
from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, Generic, Final, Optional

from pkg_resources import iter_entry_points, DistributionNotFound

__all__ = ['Plugins']

TypeT = TypeVar('TypeT', bound='type')


class Plugins(Generic[TypeT]):

    def __init__(self, base: TypeT, group: str) -> None:
        super().__init__()
        self.base: Final = base
        self.group: Final = group
        self._failures: dict[str, DistributionNotFound] = {}
        self._loaded: Optional[dict[str, TypeT]] = None

    @property
    def loaded(self) -> Mapping[str, TypeT]:
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
        loaded = self.loaded
        if name not in loaded:
            if name in self._failures:
                raise self._failures[name]
            else:
                msg = f'{name!r} is not a valid {self.group!r} plugin'
                raise ValueError(msg)
        return loaded[name]
