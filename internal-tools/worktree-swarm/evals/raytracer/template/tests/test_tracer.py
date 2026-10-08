import math
import unittest

from tests._support import close, ensure_module

ensure_module("rt.lighting", {"shade": lambda *a: (0.0, 0.0, 0.0)})
from rt import tracer  # noqa: E402
from rt.types import Hit, Material, Ray, Scene  # noqa: E402
from rt.vec import dot, normalize, sub  # noqa: E402

LOCAL = (0.5, 0.25, 0.1)


class FakeLighting:
    calls = []

    @staticmethod
    def shade(hit, view_dir, lights, ambient, occluded):
        FakeLighting.calls.append((hit, view_dir, occluded))
        return LOCAL


class Ball:
    def __init__(self, c, r, m):
        self.c, self.r, self.material = c, r, m

    def intersect(self, ray, t_min, t_max):
        oc = sub(ray.origin, self.c)
        b = dot(oc, ray.direction)
        disc = b * b - (dot(oc, oc) - self.r * self.r)
        if disc < 0:
            return None
        for t in (-b - math.sqrt(disc), -b + math.sqrt(disc)):
            if t_min < t < t_max:
                p = ray.at(t)
                n = [(p[k] - self.c[k]) / self.r for k in range(3)]
                front = dot(ray.direction, n) < 0
                return Hit(t, p, n if front else [-x for x in n], front, (0, 0), self.material)
        return None


class Wall:
    """Plane z = z0 facing +z."""
    def __init__(self, z0, m):
        self.z0, self.material = z0, m

    def intersect(self, ray, t_min, t_max):
        if abs(ray.direction[2]) < 1e-12:
            return None
        t = (self.z0 - ray.origin[2]) / ray.direction[2]
        if not t_min < t < t_max:
            return None
        front = ray.direction[2] < 0
        return Hit(t, ray.at(t), [0, 0, 1] if front else [0, 0, -1], front, (0, 0), self.material)


class ListBVH:
    def __init__(self, shapes):
        self.shapes = shapes

    def intersect(self, ray, t_min, t_max):
        best = None
        for s in self.shapes:
            h = s.intersect(ray, t_min, t_max)
            if h is not None and (best is None or h.t < best.t):
                best = h
        return best


def scene(shapes, depth=4):
    return Scene(camera=None, lights=[], ambient=(0, 0, 0), objects=shapes, bvh=ListBVH(shapes), max_depth=depth)


GLASS = Material(color=(1, 1, 1), transparency=0.9, ior=1.5)
MIRROR = Material(color=(1, 1, 1), reflect=0.8)


class TestTracer(unittest.TestCase):
    def setUp(self):
        self.saved = tracer.lighting
        tracer.lighting = FakeLighting
        FakeLighting.calls.clear()

    def tearDown(self):
        tracer.lighting = self.saved

    def test_background_and_schlick(self):
        s = scene([])
        self.assertTrue(close(tracer.background(s, [0, 0.2, 0.98]), (0.65, 0.752, 0.97)))
        self.assertTrue(close(tracer.trace(Ray([0, 0, 0], [0, 1, 0]), s), s.background_top))
        self.assertAlmostEqual(tracer.schlick(0.5, 1.5), 0.07)
        self.assertAlmostEqual(tracer.schlick(1.0, 1.5), 0.04)

    def test_opaque_calls_lighting(self):
        s = scene([Wall(-2, Material())])
        c = tracer.trace(Ray([0, 0, 0], [0, 0, -1]), s)
        self.assertTrue(close(c, LOCAL))
        hit, view, occluded = FakeLighting.calls[0]
        self.assertTrue(close(view, [0, 0, 1]))
        self.assertTrue(occluded([0, 0, 0], [0, 0, -1], 5.0))
        self.assertFalse(occluded([0, 0, 0], [0, 0, -1], 1.5))
        self.assertFalse(occluded([0, 0, 0], [0, 0, 1], math.inf))

    def test_mirror(self):
        c = tracer.trace(Ray([0, 0, 0], normalize([0, 0.3, -1])), scene([Wall(-2, MIRROR)]))
        self.assertTrue(close(c, (0.602530422886731, 0.6400700791052425, 0.7942530422886731)))

    def test_glass(self):
        s = scene([Ball([0, 0, -3], 1.0, GLASS)])
        self.assertTrue(close(tracer.trace(Ray([0, 0, 0], [0, 0, -1]), s),
                              (0.6620493231103999, 0.68352139350016, 0.80904152249344)))
        self.assertTrue(close(tracer.trace(Ray([0, 0, 0], normalize([0.25, 0.1, -1])), s),
                              (0.6885258098250722, 0.7012588460302358, 0.8122471088818927)))

    def test_total_internal_reflection(self):
        s = scene([Ball([0, 0, -3], 1.0, GLASS)])
        self.assertTrue(close(tracer.trace(Ray([0, 0, -3], normalize([0.95, 0, 0.312])), s),
                              (0.6792520551296, 0.72950089139584, 0.88423089677056)))

    def test_max_depth(self):
        s = scene([Ball([0, 0, -3], 1.0, GLASS)], depth=1)
        self.assertTrue(close(tracer.trace(Ray([0, 0, 0], [0, 0, -1]), s), (0.1184, 0.07486, 0.05374)))
        s0 = scene([Wall(-2, MIRROR)], depth=0)
        self.assertTrue(close(tracer.trace(Ray([0, 0, 0], [0, 0, -1]), s0), (0.1, 0.05, 0.02)))
