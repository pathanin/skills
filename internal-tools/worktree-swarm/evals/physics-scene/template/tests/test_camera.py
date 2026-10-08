import math
import unittest

from ballpit.camera import Camera
from ballpit.vec import add, dot, normalize, sub

EYE, TARGET = (3.0, 2.0, 4.0), (0.0, 0.5, 0.0)


class TestCamera(unittest.TestCase):
    def setUp(self):
        self.cam = Camera(EYE, TARGET, 40, 200, 100)

    def test_target_projects_to_centre(self):
        x, y = self.cam.project(TARGET)
        self.assertAlmostEqual(x, 100.0)
        self.assertAlmostEqual(y, 50.0)

    def test_centre_ray_is_forward(self):
        cam = Camera(EYE, TARGET, 40, 201, 101)
        o, d = cam.ray(100, 50)
        self.assertEqual(list(o), list(EYE))
        f = normalize(sub(TARGET, EYE))
        self.assertAlmostEqual(dot(d, f), 1.0)

    def test_round_trip_and_orientation(self):
        for px, py in [(0, 0), (199, 0), (17, 83), (150, 40)]:
            o, d = self.cam.ray(px, py)
            x, y = self.cam.project(add(o, [c * 5 for c in d]))
            self.assertAlmostEqual(x, px + 0.5)
            self.assertAlmostEqual(y, py + 0.5)
        o, d = self.cam.ray(0, 0)
        self.assertGreater(d[1], normalize(sub(TARGET, EYE))[1])   # top row looks higher

    def test_vertical_fov(self):
        o, top = self.cam.ray(100, 0)
        o, bottom = self.cam.ray(100, 99)
        angle = math.degrees(math.acos(dot(top, bottom)))
        self.assertAlmostEqual(angle, 40 * 99 / 100, delta=0.2)

    def test_behind_is_none(self):
        self.assertIsNone(self.cam.project([6.0, 3.5, 8.0]))
