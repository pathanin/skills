import math
import unittest

from rt.shapes.plane import Disk, Plane
from rt.types import Material, Ray
from rt.vec import normalize
from tests._support import close

M = Material()


class TestPlane(unittest.TestCase):
    def test_hit_and_uv(self):
        p = Plane([0, 0, 0], [0, 2, 0], M)
        h = p.intersect(Ray([2, 3, 3], [0, -1, 0]), 1e-4, math.inf)
        self.assertAlmostEqual(h.t, 3.0)
        self.assertTrue(close(h.normal, [0, 1, 0]))
        self.assertTrue(h.front_face)
        self.assertTrue(close(h.uv, (-3.0, -2.0)))
        self.assertIsNone(p.bounds())

    def test_back_side_and_parallel(self):
        p = Plane([0, 1, 0], [0, 1, 0], M)
        h = p.intersect(Ray([0, -1, 0], normalize([0, 1, 1])), 1e-4, math.inf)
        self.assertFalse(h.front_face)
        self.assertTrue(close(h.normal, [0, -1, 0]))
        self.assertAlmostEqual(h.t, 2 * math.sqrt(2))
        self.assertIsNone(p.intersect(Ray([0, 0, 0], [1, 0, 0]), 1e-4, math.inf))
        self.assertIsNone(p.intersect(Ray([0, 0, 0], [0, 1, 0]), 1e-4, 0.5))

    def test_x_normal_tangents(self):
        p = Plane([0, 0, 0], [1, 0, 0], M)
        h = p.intersect(Ray([3, 2, 5], [-1, 0, 0]), 1e-4, math.inf)
        self.assertTrue(close(h.uv, (5.0, -2.0)))


class TestDisk(unittest.TestCase):
    def setUp(self):
        self.d = Disk([1, 0, 1], [0, 1, 0], 0.5, M)

    def test_inside_and_outside(self):
        h = self.d.intersect(Ray([1, 2, 1], [0, -1, 0]), 1e-4, math.inf)
        self.assertAlmostEqual(h.t, 2.0)
        self.assertTrue(close(h.uv, (0.5, 0.5)))
        h = self.d.intersect(Ray([1.3, 2, 1], [0, -1, 0]), 1e-4, math.inf)
        self.assertTrue(close(h.uv, (0.5, 0.2)))
        self.assertIsNone(self.d.intersect(Ray([1.6, 2, 1], [0, -1, 0]), 1e-4, math.inf))

    def test_bounds(self):
        lo, hi = self.d.bounds()
        self.assertTrue(close(lo, [0.5, 0, 0.5]))
        self.assertTrue(close(hi, [1.5, 0, 1.5]))
