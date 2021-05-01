
from __future__ import annotations

import random
from abc import abstractmethod, ABCMeta
from collections.abc import Iterable, Iterator, MutableSet, Set
from typing import TypeVar
from weakref import ref, WeakKeyDictionary, WeakValueDictionary

__all__ = ['ShuffleT', 'ShuffleT_co', 'Shuffle', 'WeakShuffle']

ShuffleT = TypeVar('ShuffleT')
ShuffleT_co = TypeVar('ShuffleT_co', covariant=True)


class Shuffle(Set[ShuffleT_co], metaclass=ABCMeta):
    """A set of objects that can be accessed in a "shuffled" manner, similar to
    a deck of cards. All operations including :meth:`.choice` are *O(1)* time
    complexity.

    """

    @abstractmethod
    def choice(self) -> ShuffleT_co:
        """Choose an object from the set at random and return it. This object
        is not removed from the set.

        See Also:
            :func:`random.choice`

        Raises:
            KeyError: The set was empty.

        """
        ...


class WeakShuffle(Shuffle[ShuffleT], MutableSet[ShuffleT]):
    """An implementation of :class:`Shuffle` that holds only weak references
    to the set elements.

    Args:
        init: Initial objects to add.

    """

    def __init__(self, /, init: Iterable[ShuffleT] = []) -> None:
        super().__init__()
        self._weak_vals: WeakKeyDictionary[ShuffleT, ref[ShuffleT]] = \
            WeakKeyDictionary()
        self._weak_vals_rev: WeakValueDictionary[ref[ShuffleT], ShuffleT] = \
            WeakValueDictionary()
        self._indexes: dict[ref[ShuffleT], int] = {}
        self._values: list[ref[ShuffleT]] = []
        for val in init:
            self.add(val)

    def _finalize(self, weak_val: ref[ShuffleT]) -> None:
        index = self._indexes.pop(weak_val, None)
        if index is not None:
            values = self._values
            end_index = len(values) - 1
            if index < end_index:
                values[index] = values[end_index]
            del self._values[end_index]

    def add(self, val: ShuffleT) -> None:
        if val not in self._weak_vals:
            weak_val = ref(val, self._finalize)
            self._weak_vals[val] = weak_val
            self._weak_vals_rev[weak_val] = val
            self._indexes[weak_val] = len(self._values)
            self._values.append(weak_val)

    def discard(self, val: ShuffleT) -> None:
        weak_val = self._weak_vals.get(val)
        if weak_val is not None:
            del self._weak_vals[val]
            del self._weak_vals_rev[weak_val]
            self._finalize(weak_val)

    def choice(self) -> ShuffleT:
        """Choose an object from the set at random and return it. This object
        is not removed from the set.

        See Also:
            :func:`random.choice`

        Raises:
            KeyError: The set was empty.

        """
        try:
            weak_val = random.choice(self._values)
        except IndexError:
            raise KeyError('choice from an empty set')
        val = weak_val()
        assert val is not None
        return val

    def __contains__(self, val: object) -> bool:
        return val in self._weak_vals

    def __iter__(self) -> Iterator[ShuffleT]:
        return self._weak_vals.keys()

    def __len__(self) -> int:
        return len(self._weak_vals)
