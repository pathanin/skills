import math
import unittest

from rt.shapes.box import Box
from rt.types import Material, Ray
from rt.vec import normalize
from tests._support import close

M = Material()


class TestBox(unittest.TestCase):
    def setUp(self):
        self.b = Box([1, 2, 3], [-1, 0, 1], M)   # corners given unsorted

    def test_bounds_sorted(self):
        lo, hi = self.b.bounds()
        self.assertEqual(list(lo), [-1, 0, 1])
        self.assertEqual(list(hi), [1, 2, 3])

    def test_hit_each_face(self):
        cases = [([-5, 1, 2], [1, 0, 0], 4, [-1, 0, 0]), ([5, 1, 2], [-1, 0, 0], 4, [1, 0, 0]),
                 ([0, -3, 2], [0, 1, 0], 3, [0, -1, 0]), ([0, 6, 2], [0, -1, 0], 4, [0, 1, 0]),
                 ([0, 1, -1], [0, 0, 1], 2, [0, 0, -1]), ([0, 1, 9], [0, 0, -1], 6, [0, 0, 1])]
        for o, d, t, n in cases:
            h = self.b.intersect(Ray(o, d), 1e-4, math.inf)
            self.assertAlmostEqual(h.t, t, msg=str(o))
            self.assertTrue(close(h.normal, n), msg=f"{o} {h.normal}")
            self.assertTrue(h.front_face)

    def test_uv(self):
        h = self.b.intersect(Ray([-5, 1.5, 2.5], [1, 0, 0]), 1e-4, math.inf)   # x face: u from y, v from z
        self.assertTrue(close(h.uv, (0.75, 0.75)))
        h = self.b.intersect(Ray([0.5, 6, 1.5], [0, -1, 0]), 1e-4, math.inf)    # y face: u from x, v from z
        self.assertTrue(close(h.uv, (0.75, 0.25)))

    def test_inside(self):
        h = self.b.intersect(Ray([0, 1, 2], [0, 0, 1]), 1e-4, math.inf)
        self.assertAlmostEqual(h.t, 1.0)
        self.assertFalse(h.front_face)
        self.assertTrue(close(h.normal, [0, 0, -1]))

    def test_misses(self):
        self.assertIsNone(self.b.intersect(Ray([-5, 5, 2], [1, 0, 0]), 1e-4, math.inf))
        self.assertIsNone(self.b.intersect(Ray([-5, 1, 2], normalize([1, 1, 0])), 1e-4, math.inf))
        self.assertIsNone(self.b.intersect(Ray([-5, 1, 2], [1, 0, 0]), 1e-4, 3.0))
        self.assertIsNone(self.b.intersect(Ray([5, 1, 2], [1, 0, 0]), 1e-4, math.inf))
