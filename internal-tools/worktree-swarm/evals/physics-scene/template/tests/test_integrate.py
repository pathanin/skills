import unittest

from ballpit.integrate import advance
from ballpit.world import Ball, World


class TestAdvance(unittest.TestCase):
    def test_semi_implicit_euler(self):
        w = World([Ball([0.0, 1.0, 0.0], [1.0, 0.0, -2.0], 0.1, 1.0, (0, 0, 0))], gravity=-10.0)
        advance(w, 0.1)
        b = w.balls[0]
        for got, want in zip(b.vel, [1.0, -1.0, -2.0]):
            self.assertAlmostEqual(got, want)
        for got, want in zip(b.pos, [0.1, 0.9, -0.2]):
            self.assertAlmostEqual(got, want)
        advance(w, 0.1)
        self.assertAlmostEqual(b.vel[1], -2.0)
        self.assertAlmostEqual(b.pos[1], 0.7)
