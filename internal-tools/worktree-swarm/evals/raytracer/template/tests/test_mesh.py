import math
import unittest

from tests._support import ensure_triangle

ensure_triangle()
from rt import mesh  # noqa: E402
from rt.types import Material  # noqa: E402
from rt.vec import dot, length, sub  # noqa: E402

M = Material()


def outward(tris, ref):
    """Share of triangles whose geometric normal points away from ref(triangle) -> point."""
    return sum(1 for t in tris if dot(sub(t.a, ref(t)), t.geo_normal) > 0) / len(tris)


class TestIcosphere(unittest.TestCase):
    def test_counts(self):
        for s, n in ((0, 20), (1, 80), (2, 320)):
            self.assertEqual(len(mesh.icosphere([0, 0, 0], 1.0, s, M)), n)

    def test_on_surface_outward_normals(self):
        c = [1.0, 2.0, -1.0]
        tris = mesh.icosphere(c, 0.5, 2, M)
        for t in tris:
            for v, n in zip((t.a, t.b, t.c), t.normals):
                self.assertAlmostEqual(length(sub(v, c)), 0.5)
                self.assertAlmostEqual(length(n), 1.0)
                self.assertGreater(dot(n, sub(v, c)), 0.49)
        self.assertEqual(outward(tris, lambda t: c), 1.0)
        self.assertIs(tris[0].material, M)

    def test_shared_midpoints(self):
        tris = mesh.icosphere([0, 0, 0], 1.0, 1, M)
        verts = {tuple(round(x, 9) for x in v) for t in tris for v in (t.a, t.b, t.c)}
        self.assertEqual(len(verts), 42)


class TestTorus(unittest.TestCase):
    def test_counts_and_shape(self):
        c, R, r = [0.0, 1.0, 0.0], 1.0, 0.25
        tris = mesh.torus(c, R, r, 24, 12, M)
        self.assertEqual(len(tris), 24 * 12 * 2)
        for t in tris[:60]:
            for v in (t.a, t.b, t.c):
                ring = math.hypot(v[0] - c[0], v[2] - c[2])
                self.assertAlmostEqual(math.hypot(ring - R, v[1] - c[1]), r)

        def tube_centre(t):
            x, z = t.a[0] - c[0], t.a[2] - c[2]
            k = R / math.hypot(x, z)
            return [c[0] + x * k, c[1], c[2] + z * k]
        self.assertGreater(outward(tris, tube_centre), 0.99)


class TestCylinder(unittest.TestCase):
    def test_counts_and_shape(self):
        base = [1.0, 0.0, 1.0]
        tris = mesh.cylinder(base, 0.5, 2.0, 16, M)
        self.assertEqual(len(tris), 64)
        self.assertEqual(len(mesh.cylinder(base, 0.5, 2.0, 16, M, caps=False)), 32)
        ys = {round(v[1], 9) for t in tris for v in (t.a, t.b, t.c)}
        self.assertEqual(ys, {0.0, 2.0})
        mid = [1.0, 1.0, 1.0]
        self.assertEqual(outward(tris, lambda t: mid), 1.0)
