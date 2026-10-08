import math
import unittest

from rt.shapes.triangle import Triangle
from rt.types import Material, Ray
from rt.vec import normalize
from tests._support import close

M = Material()


class TestTriangle(unittest.TestCase):
    def setUp(self):
        self.t = Triangle([0, 0, 0], [2, 0, 0], [0, 2, 0], M)

    def test_front_hit(self):
        h = self.t.intersect(Ray([0.5, 0.5, 3], [0, 0, -1]), 1e-4, math.inf)
        self.assertAlmostEqual(h.t, 3.0)
        self.assertTrue(close(h.normal, [0, 0, 1]))
        self.assertTrue(h.front_face)
        self.assertTrue(close(h.uv, (0.25, 0.25)))
        self.assertTrue(close(self.t.geo_normal, [0, 0, 1]))

    def test_back_hit_flips(self):
        h = self.t.intersect(Ray([0.5, 0.5, -3], [0, 0, 1]), 1e-4, math.inf)
        self.assertFalse(h.front_face)
        self.assertTrue(close(h.normal, [0, 0, -1]))

    def test_misses(self):
        for o in ([1.5, 1.5, 3], [-0.1, 0.5, 3], [0.5, -0.1, 3]):
            self.assertIsNone(self.t.intersect(Ray(o, [0, 0, -1]), 1e-4, math.inf), o)
        self.assertIsNone(self.t.intersect(Ray([0.5, 0.5, 3], [1, 0, 0]), 1e-4, math.inf))
        self.assertIsNone(self.t.intersect(Ray([0.5, 0.5, 3], [0, 0, -1]), 1e-4, 2.0))

    def test_smooth_normals(self):
        t = Triangle([0, 0, 0], [2, 0, 0], [0, 2, 0], M, normals=[[0, 0, 2], [1, 0, 1], [0, 1, 1]])
        h = t.intersect(Ray([0, 0, 3], normalize([0.001, 0.001, -1])), 1e-4, math.inf)
        self.assertTrue(close(h.normal, [0, 0, 1], places=2))
        h = t.intersect(Ray([1, 0, 3], [0, 0, -1]), 1e-4, math.inf)    # u = 0.5, v = 0
        self.assertTrue(close(h.normal, normalize([0.5 * 0 + 0.5 * 0.7071, 0, 0.5 + 0.5 * 0.7071]), places=3))

    def test_bounds(self):
        lo, hi = Triangle([1, -2, 3], [0, 4, 3], [2, 0, -1], M).bounds()
        self.assertEqual(list(lo), [0, -2, -1])
        self.assertEqual(list(hi), [2, 4, 3])
