import unittest

from ballpit.collide import resolve
from ballpit.vec import length, sub
from ballpit.world import Ball, World


def pair(p1, v1, p2, v2, m1=1.0, m2=1.0, e=1.0):
    return World([Ball(list(p1), list(v1), 0.5, m1, (0, 0, 0)), Ball(list(p2), list(v2), 0.5, m2, (0, 0, 0))],
                 restitution=e)


def momentum(w):
    return [sum(b.mass * b.vel[k] for b in w.balls) for k in range(3)]


class TestCollide(unittest.TestCase):
    def test_head_on_equal_mass_swaps(self):
        w = pair([0, 1, 0], [1, 0, 0], [0.9, 1, 0], [-1, 0, 0])
        resolve(w)
        a, b = w.balls
        self.assertAlmostEqual(a.vel[0], -1.0)
        self.assertAlmostEqual(b.vel[0], 1.0)
        self.assertAlmostEqual(length(sub(b.pos, a.pos)), 1.0)
        self.assertAlmostEqual(a.pos[0], -0.05)

    def test_momentum_and_restitution(self):
        w = pair([0, 1, 0], [2, 0.5, 0], [0.6, 1.6, 0.2], [-1, 0, 0.3], m1=1.0, m2=3.0, e=0.9)
        before = momentum(w)
        resolve(w)
        for got, want in zip(momentum(w), before):
            self.assertAlmostEqual(got, want)
        a, b = w.balls
        self.assertAlmostEqual(length(sub(b.pos, a.pos)), 1.0)

    def test_inverse_mass_push(self):
        w = pair([0, 1, 0], [0, 0, 0], [0.8, 1, 0], [0, 0, 0], m1=1.0, m2=3.0)
        resolve(w)
        self.assertAlmostEqual(w.balls[0].pos[0], -0.15)
        self.assertAlmostEqual(w.balls[1].pos[0], 0.85)

    def test_receding_no_impulse(self):
        w = pair([0, 1, 0], [-1, 0, 0], [0.9, 1, 0], [1, 0, 0])
        resolve(w)
        self.assertEqual(w.balls[0].vel, [-1, 0, 0])
        self.assertEqual(w.balls[1].vel, [1, 0, 0])

    def test_apart_and_coincident(self):
        w = pair([0, 1, 0], [1, 0, 0], [2, 1, 0], [-1, 0, 0])
        resolve(w)
        self.assertEqual(w.balls[0].vel, [1, 0, 0])
        w = pair([0, 1, 0], [0, 0, 0], [0, 1, 0], [0, 0, 0])
        resolve(w)  # must not raise
