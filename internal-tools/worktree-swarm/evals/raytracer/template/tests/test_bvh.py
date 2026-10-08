import math
import random
import unittest

from rt.bvh import build
from rt.types import Hit, Material, Ray
from rt.vec import dot, normalize, sub

M = Material()


class Ball:
    """Minimal shape for BVH tests: a sphere with the shape protocol."""
    def __init__(self, c, r):
        self.c, self.r, self.material, self.tests = c, r, M, 0

    def intersect(self, ray, t_min, t_max):
        self.tests += 1
        oc = sub(ray.origin, self.c)
        b = dot(oc, ray.direction)
        disc = b * b - (dot(oc, oc) - self.r * self.r)
        if disc < 0:
            return None
        for t in (-b - math.sqrt(disc), -b + math.sqrt(disc)):
            if t_min < t < t_max:
                return Hit(t, ray.at(t), [0, 1, 0], True, (0, 0), self)
        return None

    def bounds(self):
        return [x - self.r for x in self.c], [x + self.r for x in self.c]


class Floor:
    material = M

    def intersect(self, ray, t_min, t_max):
        if ray.direction[1] >= 0:
            return None
        t = -ray.origin[1] / ray.direction[1]
        return Hit(t, ray.at(t), [0, 1, 0], True, (0, 0), self) if t_min < t < t_max else None

    def bounds(self):
        return None


def brute(shapes, ray, t_min, t_max):
    best = None
    for s in shapes:
        h = s.intersect(ray, t_min, t_max)
        if h is not None and (best is None or h.t < best.t):
            best = h
    return best


class TestBVH(unittest.TestCase):
    def test_matches_brute_force(self):
        rng = random.Random(7)
        shapes = [Ball([rng.uniform(-5, 5), rng.uniform(0.5, 5), rng.uniform(-5, 5)], rng.uniform(0.1, 0.6))
                  for _ in range(200)] + [Floor()]
        tree = build(shapes)
        for _ in range(400):
            o = [rng.uniform(-8, 8), rng.uniform(1, 8), rng.uniform(-8, 8)]
            d = normalize([rng.uniform(-1, 1), rng.uniform(-1, 0.5), rng.uniform(-1, 1)])
            want = brute(shapes, Ray(o, d), 1e-4, math.inf)
            got = tree.intersect(Ray(o, d), 1e-4, math.inf)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertIs(got.material, want.material)
                self.assertAlmostEqual(got.t, want.t)

    def test_prunes_and_is_shallow(self):
        balls = [Ball([x * 2.0, 0, 0], 0.5) for x in range(256)]
        tree = build(balls, leaf_size=4)
        self.assertLessEqual(tree.depth(), 10)
        tree.intersect(Ray([0, 5, 0], [0, -1, 0]), 1e-4, math.inf)
        self.assertLess(sum(b.tests for b in balls), 20)

    def test_t_range_and_empty(self):
        tree = build([Ball([0, 0, -5], 1)])
        self.assertIsNone(tree.intersect(Ray([0, 0, 0], [0, 0, -1]), 1e-4, 3.0))
        self.assertIsNone(build([]).intersect(Ray([0, 0, 0], [0, 0, -1]), 1e-4, math.inf))
        self.assertEqual(build([Floor()]).intersect(Ray([0, 2, 0], [0, -1, 0]), 1e-4, math.inf).t, 2.0)
