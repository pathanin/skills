import math
import unittest

from rt.shapes.sphere import Sphere
from rt.types import Material, Ray
from tests._support import close

M = Material()


class TestSphere(unittest.TestCase):
    def setUp(self):
        self.s = Sphere([0, 0, -5], 1.0, M)

    def test_outside_hit(self):
        h = self.s.intersect(Ray([0, 0, 0], [0, 0, -1]), 1e-4, math.inf)
        self.assertAlmostEqual(h.t, 4.0)
        self.assertTrue(close(h.point, [0, 0, -4]))
        self.assertTrue(close(h.normal, [0, 0, 1]))
        self.assertTrue(h.front_face)
        self.assertIs(h.material, M)

    def test_inside_hit_flips_normal(self):
        h = self.s.intersect(Ray([0, 0, -5], [1, 0, 0]), 1e-4, math.inf)
        self.assertAlmostEqual(h.t, 1.0)
        self.assertFalse(h.front_face)
        self.assertTrue(close(h.normal, [-1, 0, 0]))

    def test_range_and_miss(self):
        self.assertIsNone(self.s.intersect(Ray([0, 0, 0], [0, 0, -1]), 1e-4, 3.9))
        h = self.s.intersect(Ray([0, 0, 0], [0, 0, -1]), 4.5, math.inf)
        self.assertAlmostEqual(h.t, 6.0)
        self.assertIsNone(self.s.intersect(Ray([0, 2, 0], [0, 0, -1]), 1e-4, math.inf))
        self.assertIsNone(self.s.intersect(Ray([0, 0, 0], [0, 0, 1]), 1e-4, math.inf))

    def test_uv(self):
        s = Sphere([0, 0, 0], 2.0, M)
        h = s.intersect(Ray([5, 0, 0], [-1, 0, 0]), 1e-4, math.inf)
        self.assertTrue(close(h.uv, (0.5, 0.5)))
        h = s.intersect(Ray([0, 5, 0], [0, -1, 0]), 1e-4, math.inf)
        self.assertAlmostEqual(h.uv[1], 1.0)
        h = s.intersect(Ray([0, 0, 5], [0, 0, -1]), 1e-4, math.inf)
        self.assertTrue(close(h.uv, (0.25, 0.5)))

    def test_bounds(self):
        lo, hi = self.s.bounds()
        self.assertTrue(close(lo, [-1, -1, -6]))
        self.assertTrue(close(hi, [1, 1, -4]))
