import unittest

from rt import textures as T
from tests._support import close

A, B = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)


class TestTextures(unittest.TestCase):
    def test_solid(self):
        self.assertEqual(tuple(T.Solid((0.1, 0.2, 0.3)).sample((0, 0), [5, 5, 5])), (0.1, 0.2, 0.3))

    def test_checker(self):
        c = T.Checker(0.5, A, B)
        self.assertEqual(tuple(c.sample((0, 0), [0.1, 0.0, 0.1])), A)
        self.assertEqual(tuple(c.sample((0, 0), [0.6, 0.0, 0.1])), B)
        self.assertEqual(tuple(c.sample((0, 0), [-0.1, 0.0, 0.1])), B)
        self.assertEqual(tuple(c.sample((0, 0), [-0.1, 0.0, -0.1])), A)
        self.assertEqual(tuple(c.sample((0, 0), [0.6, 0.0, 0.6])), A)
        self.assertEqual(tuple(c.sample((0, 0), [0.1, -1e-12, 0.1])), A)   # floor at y = 0 doesn't flicker

    def test_stripes(self):
        s = T.Stripes(4, A, B)
        self.assertEqual([tuple(s.sample((u, 0.3), [0, 0, 0])) for u in (0.1, 0.3, 0.6, 0.8)], [A, B, A, B])

    def test_value_noise(self):
        self.assertAlmostEqual(T.value_noise([1.3, 2.7, -0.4]), 0.4224151799325064)
        self.assertAlmostEqual(T.value_noise([0, 0, 0]), 0.0)
        self.assertAlmostEqual(T.value_noise([2, 3, 4], seed=5), 0.8061050286523823)
        for p in ([0.1, 0.2, 0.3], [7.5, -3.2, 1.1], [100.25, 0.5, -42.75]):
            v = T.value_noise(p)
            self.assertTrue(0 <= v < 1)
            self.assertAlmostEqual(T.value_noise([p[0] + 1e-7, p[1], p[2]]), v, places=5)

    def test_fbm_noise_marble(self):
        self.assertAlmostEqual(T.fbm([0.3, 1.1, 2.2]), 0.573882864349406)
        self.assertAlmostEqual(T.fbm([0.3, 1.1, 2.2], 2, 1), 0.5508675914131088)
        n = T.Noise(2.0, (0, 0, 0), (1, 0.5, 0.25), seed=3).sample((0, 0), [0.4, 0.2, -0.7])
        self.assertTrue(close(n, (0.4351265233237371, 0.21756326166186854, 0.10878163083093427)))
        m = T.Marble(3.0, (1, 1, 1), (0, 0, 0.5), 1.2).sample((0, 0), [0.25, 0.6, 0.1])
        self.assertTrue(close(m, (0.9775835724375137, 0.9775835724375137, 0.9887917862187569)))
