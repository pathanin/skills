import math
import unittest

from rt import tonemap


class TestTonemap(unittest.TestCase):
    def test_luminance(self):
        self.assertAlmostEqual(tonemap.luminance((1, 1, 1)), 1.0)
        self.assertAlmostEqual(tonemap.luminance((0, 1, 0)), 0.7152)

    def test_to_srgb8(self):
        self.assertEqual(tuple(tonemap.to_srgb8((0, 0, 0))), (0, 0, 0))
        self.assertEqual(tuple(tonemap.to_srgb8((100, -1, 0.001))), (255, 0, 3))
        v = 1 - math.exp(-1.0)   # green: 0.5 * exposure 2
        want = round((1.055 * v ** (1 / 2.4) - 0.055) * 255)
        self.assertEqual(tuple(tonemap.to_srgb8((0.25, 0.5, 1.0), exposure=2.0))[1], want)
        # exposure scales the colour before the curve
        self.assertEqual(tuple(tonemap.to_srgb8((0.25, 0.5, 1.0), exposure=2.0)),
                         tuple(tonemap.to_srgb8((0.5, 1.0, 2.0))))
        for c in tonemap.to_srgb8((0.3, 0.6, 0.9)):
            self.assertIsInstance(c, int)

    def test_auto_exposure(self):
        img = [[(0.5, 0.5, 0.5)] * 4 for _ in range(3)]
        self.assertAlmostEqual(tonemap.auto_exposure(img), 0.18 / (1e-4 + 0.5))
        img[0][0] = (-1, -1, -1)
        logs = [math.log(1e-4 + 0.5)] * 11 + [math.log(1e-4)]
        self.assertAlmostEqual(tonemap.auto_exposure(img, key=0.3), 0.3 / math.exp(sum(logs) / 12))

    def test_to_rows(self):
        rows = tonemap.to_rows([[(0, 0, 0), (1, 1, 1)], [(2, 2, 2), (0.1, 0.1, 0.1)]], 1.0)
        self.assertEqual(len(rows), 2)
        self.assertEqual(tuple(rows[0][0]), (0, 0, 0))
        self.assertEqual(tuple(rows[1][0]), tuple(tonemap.to_srgb8((2, 2, 2), 1.0)))
