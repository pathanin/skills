import math
import unittest

from rt.camera import Camera
from rt.vec import dot, normalize, sub
from tests._support import close


class TestCamera(unittest.TestCase):
    def setUp(self):
        self.cam = Camera([0, 2, 6], [0, 1, 0], [0, 1, 0], 40, 200, 100)

    def test_centre_and_origin(self):
        r = self.cam.ray(100, 50, 0.0, 0.0)
        self.assertTrue(close(r.direction, normalize(sub([0, 1, 0], [0, 2, 6]))))
        self.assertEqual(list(r.origin), [0, 2, 6])
        self.assertAlmostEqual(math.sqrt(dot(r.direction, r.direction)), 1.0)

    def test_vertical_fov_and_orientation(self):
        top = self.cam.ray(100, 0, 0.0, 0.0).direction
        bottom = self.cam.ray(100, 100, 0.0, 0.0).direction
        self.assertAlmostEqual(math.degrees(math.acos(dot(top, bottom))), 40.0)
        self.assertGreater(top[1], bottom[1])
        left = self.cam.ray(0, 50, 0.0, 0.0).direction
        right = self.cam.ray(200, 50, 0.0, 0.0).direction
        self.assertLess(left[0], 0)
        self.assertGreater(right[0], 0)
        half_w = math.tan(math.radians(20)) * 2
        self.assertAlmostEqual(math.degrees(math.acos(dot(left, right))), 2 * math.degrees(math.atan(half_w)), places=5)

    def test_default_pixel_centre(self):
        a = self.cam.ray(10, 20).direction
        b = self.cam.ray(10, 20, 0.5, 0.5).direction
        self.assertTrue(close(a, b))

    def test_orbit(self):
        cam = Camera.orbit([1, 0.5, -1], 4.0, 2.0, 90, 40, 64, 48)
        self.assertTrue(close(cam.eye, [5, 2.5, -1]))
        d = cam.ray(32, 24, 0.0, 0.0).direction
        self.assertTrue(close(d, normalize([-4, -2, 0])))
        self.assertEqual((cam.width, cam.height), (64, 48))
