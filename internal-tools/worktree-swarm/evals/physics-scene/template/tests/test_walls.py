import unittest

from ballpit.walls import resolve
from ballpit.world import Ball, World


def world(pos, vel, e=0.5):
    return World([Ball(list(pos), list(vel), 0.1, 1.0, (0, 0, 0))], half_width=1.0, height=3.0, restitution=e)


class TestWalls(unittest.TestCase):
    def test_floor_bounce(self):
        w = world([0.2, 0.05, 0.0], [1.0, -4.0, 0.5])
        resolve(w)
        b = w.balls[0]
        self.assertAlmostEqual(b.pos[1], 0.1)
        self.assertAlmostEqual(b.vel[1], 2.0)
        self.assertEqual(b.vel[0], 1.0)
        self.assertEqual(b.vel[2], 0.5)

    def test_every_wall(self):
        cases = [([0.95, 1, 0], [3, 0, 0], 0, 0.9, -1.5), ([-0.95, 1, 0], [-3, 0, 0], 0, -0.9, 1.5),
                 ([0, 1, 0.95], [0, 0, 3], 2, 0.9, -1.5), ([0, 1, -0.95], [0, 0, -3], 2, -0.9, 1.5),
                 ([0, 2.95, 0], [0, 3, 0], 1, 2.9, -1.5)]
        for pos, vel, axis, want_pos, want_vel in cases:
            w = world(pos, vel)
            resolve(w)
            self.assertAlmostEqual(w.balls[0].pos[axis], want_pos, msg=str(pos))
            self.assertAlmostEqual(w.balls[0].vel[axis], want_vel, msg=str(pos))

    def test_moving_away_keeps_velocity(self):
        w = world([0.0, 0.05, 0.0], [0.0, 2.0, 0.0])
        resolve(w)
        self.assertAlmostEqual(w.balls[0].pos[1], 0.1)
        self.assertEqual(w.balls[0].vel[1], 2.0)

    def test_inside_untouched(self):
        w = world([0.3, 1.0, -0.2], [1.0, -1.0, 1.0])
        resolve(w)
        self.assertEqual(w.balls[0].pos, [0.3, 1.0, -0.2])
        self.assertEqual(w.balls[0].vel, [1.0, -1.0, 1.0])
