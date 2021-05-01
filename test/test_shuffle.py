
from __future__ import annotations

from unittest import TestCase

from swimprotocol.shuffle import WeakShuffle


class _T:
    pass


class TestWeakShuffle(TestCase):

    def test_empty(self) -> None:
        shuffle: WeakShuffle[_T] = WeakShuffle()
        self.assertEqual(0, len(shuffle))
        self.assertRaises(KeyError, shuffle.choice)

    def test_add_one(self) -> None:
        val = _T()
        shuffle = WeakShuffle([val])
        self.assertEqual(1, len(shuffle))
        self.assertEqual(set([val]), set(shuffle))
        self.assertIn(val, shuffle)
        self.assertEqual(val, shuffle.choice())
        self.assertEqual(val, next(iter(shuffle)))

    def test_add_many(self) -> None:
        vals = [_T(), _T(), _T()]
        shuffle = WeakShuffle(vals)
        self.assertEqual(3, len(shuffle))
        self.assertEqual(set(vals), set(shuffle))
        for val in vals:
            self.assertIn(val, shuffle)
        for i in range(100):
            self.assertIn(shuffle.choice(), vals)

    def test_discard(self) -> None:
        vals = [_T(), _T(), _T()]
        shuffle = WeakShuffle(vals)
        shuffle.discard(vals[1])
        self.assertEqual(2, len(shuffle))
        self.assertEqual(set([vals[0], vals[2]]), set(shuffle))
        for i in range(100):
            self.assertIn(shuffle.choice(), vals)
        shuffle.discard(vals[2])
        self.assertEqual(1, len(shuffle))
        self.assertEqual(set([vals[0]]), set(shuffle))
        for i in range(100):
            self.assertIn(shuffle.choice(), vals)
        shuffle.discard(vals[0])
        self.assertEqual(0, len(shuffle))
        self.assertEqual(set(), set(shuffle))
        self.assertRaises(KeyError, shuffle.choice)

    def test_disappear(self) -> None:
        vals = [_T(), _T(), _T()]
        shuffle = WeakShuffle(vals)
        del vals[1]
        self.assertEqual(2, len(shuffle))
        self.assertEqual(set(vals), set(shuffle))
        for i in range(100):
            self.assertIn(shuffle.choice(), vals)
        del vals[1]
        self.assertEqual(1, len(shuffle))
        self.assertEqual(set(vals), set(shuffle))
        for i in range(100):
            self.assertIn(shuffle.choice(), vals)
        del vals
        self.assertEqual(0, len(shuffle))
        self.assertEqual(set(), set(shuffle))
        self.assertRaises(KeyError, shuffle.choice)
