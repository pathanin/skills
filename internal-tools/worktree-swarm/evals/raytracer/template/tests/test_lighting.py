import math
import unittest

from rt import lighting
from rt.types import DirectionalLight, Hit, Material, PointLight
from rt.vec import normalize
from tests._support import close


class Tex:
    def sample(self, uv, point):
        return (uv[0], uv[1], 0.5)


def hit(material, normal=(0, 1, 0), point=(0, 0, 0), uv=(0.2, 0.4)):
    return Hit(1.0, list(point), list(normal), True, uv, material)


NEVER = lambda o, d, t: False   # noqa: E731


class TestLighting(unittest.TestCase):
    def test_surface_color(self):
        self.assertEqual(tuple(lighting.surface_color(hit(Material(color=(0.3, 0.2, 0.1))))), (0.3, 0.2, 0.1))
        self.assertEqual(tuple(lighting.surface_color(hit(Material(texture=Tex())))), (0.2, 0.4, 0.5))

    def test_ambient_only(self):
        c = lighting.shade(hit(Material(color=(0.5, 1.0, 0.2))), [0, 1, 0], [], (0.1, 0.2, 0.3), NEVER)
        self.assertTrue(close(c, (0.05, 0.2, 0.06)))

    def test_point_light_diffuse_falloff(self):
        m = Material(color=(1.0, 0.5, 0.25), diffuse=0.8)
        light = PointLight([0, 2, 0], (1.0, 1.0, 1.0), 8.0)
        c = lighting.shade(hit(m), [0, 1, 0], [light], (0, 0, 0), NEVER)
        self.assertTrue(close(c, (1.6, 0.8, 0.4)))   # 8 / 2^2 * 0.8 * base * 1

    def test_directional_and_specular(self):
        m = Material(color=(1, 1, 1), diffuse=0.5, specular=0.3, shininess=10)
        d = normalize([1, 1, 0])
        light = DirectionalLight(d, (1.0, 0.5, 1.0), 2.0)
        view = normalize([-1, 1, 0])
        c = lighting.shade(hit(m), view, [light], (0, 0, 0), NEVER)
        ndl = d[1]
        spec = 0.3 * 1.0 ** 10                        # H is the normal
        self.assertTrue(close(c, (2 * (0.5 * ndl + spec), 1 * (0.5 * ndl + spec), 2 * (0.5 * ndl + spec))))

    def test_shininess_exponent(self):
        m = Material(color=(0, 0, 0), diffuse=0.0, specular=1.0, shininess=20)
        light = DirectionalLight([0, 1, 0], (1, 1, 1), 1.0)
        view = normalize([1, 1, 0])
        c = lighting.shade(hit(m), view, [light], (0, 0, 0), NEVER)
        n_dot_h = normalize([view[0], view[1] + 1, view[2]])[1]
        self.assertAlmostEqual(c[0], n_dot_h ** 20)

    def test_shadow_and_backface(self):
        m = Material(color=(1, 1, 1))
        seen = []

        def blocked(o, d, t):
            seen.append((o, d, t))
            return True
        light = PointLight([0, 4, 0], (1, 1, 1), 16.0)
        c = lighting.shade(hit(m, point=(0, 0, 0)), [0, 1, 0], [light], (0.1, 0.1, 0.1), blocked)
        self.assertTrue(close(c, (0.1, 0.1, 0.1)))
        o, d, t = seen[0]
        self.assertTrue(close(o, [0, 1e-4, 0]))
        self.assertTrue(close(d, [0, 1, 0]))
        self.assertAlmostEqual(t, 4.0)
        below = PointLight([0, -4, 0], (1, 1, 1), 16.0)
        sun = DirectionalLight([0, 1, 0], (1, 1, 1), 1.0)
        seen.clear()
        lighting.shade(hit(m), [0, 1, 0], [below], (0, 0, 0), blocked)
        self.assertEqual(seen, [])                   # facing away: no shadow ray at all
        lighting.shade(hit(m), [0, 1, 0], [sun], (0, 0, 0), blocked)
        self.assertEqual(seen[0][2], math.inf)
