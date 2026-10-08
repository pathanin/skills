import math
import unittest

from ballpit.camera import Camera
from ballpit.raster import render
from ballpit.vec import mul, normalize, sub
from ballpit.world import Ball, World

L = normalize([-0.4, 1.0, 0.3])
BALL = [0.0, 0.5, 0.0]


class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = World([Ball(list(BALL), [0, 0, 0], 0.4, 1.0, (220, 40, 40))], half_width=2.0)
        cls.cam = Camera((0.0, 1.6, 3.0), (0.0, 0.4, 0.0), 45, 64, 48)
        cls.img = render(cls.world, cls.cam)

    def px(self, point):
        x, y = self.cam.project(point)
        return self.img[int(y)][int(x)]

    def test_shape_and_type(self):
        self.assertEqual(len(self.img), 48)
        self.assertTrue(all(len(r) == 64 for r in self.img))
        for r, g, b in (self.img[0][0], self.img[47][63], self.img[20][30]):
            for c in (r, g, b):
                self.assertIsInstance(c, int)
                self.assertTrue(0 <= c <= 255)

    def test_background_gradient(self):
        self.assertEqual(self.img[0][0], (30, 34, 48))

    def test_ball_is_red_and_lit_side_brighter(self):
        r, g, b = self.px(BALL)
        self.assertGreater(r, 100)
        self.assertLess(g, r / 3)
        lit = self.px([BALL[0] + L[0] * 0.39, BALL[1] + L[1] * 0.39, BALL[2] + L[2] * 0.39])
        dark = self.px([BALL[0] + 0.3, BALL[1] - 0.25, BALL[2] + 0.1])
        self.assertGreater(lit[0], dark[0])

    def test_shadow_is_ambient_only(self):
        # the floor point straight down the light ray through the ball centre is shadowed
        shadow = sub(BALL, mul(L, BALL[1] / L[1]))
        self.assertIn(self.px(shadow), {(50, 50, 50), (30, 30, 30)})

    def test_lit_floor(self):
        r, g, b = self.px([1.2, 0.0, 1.0])
        self.assertEqual(r, g)
        self.assertEqual(g, b)
        brightness = 0.25 + 0.75 * L[1]
        self.assertIn(r, {round(200 * brightness), round(120 * brightness)})
