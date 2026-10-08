import itertools
import unittest

from ballpit.scene import pyramid
from ballpit.vec import length, sub


class TestPyramid(unittest.TestCase):
    def setUp(self):
        self.w = pyramid(layers=4)

    def test_counts_and_cue(self):
        self.assertEqual(len(self.w.balls), 21)
        cue = self.w.balls[-1]
        self.assertEqual(cue.mass, 2.0)
        self.assertEqual(list(cue.vel), [6.0, 0.6, 0.0])
        self.assertEqual(tuple(cue.color), (240, 240, 240))
        self.assertTrue(all(list(b.vel) == [0, 0, 0] for b in self.w.balls[:-1]))

    def test_no_overlap_and_above_floor(self):
        for a, b in itertools.combinations(self.w.balls, 2):
            self.assertGreaterEqual(length(sub(a.pos, b.pos)), a.radius + b.radius)
        for b in self.w.balls:
            self.assertGreaterEqual(b.pos[1] - b.radius, 0)

    def test_stacked_and_centred(self):
        bottom, top = self.w.balls[0], self.w.balls[19]
        self.assertAlmostEqual(bottom.pos[1], 0.12 * 1.001)
        self.assertAlmostEqual(top.pos[0], 0.0)
        self.assertAlmostEqual(top.pos[2], 0.0)
        self.assertAlmostEqual(top.pos[1], 0.12 * 1.001 + 3 * 0.24024 * (2 / 3) ** 0.5)
        # every upper ball rests on three below it
        for b in self.w.balls[10:20]:
            touching = [o for o in self.w.balls[:20] if o is not b and o.pos[1] < b.pos[1]
                        and length(sub(o.pos, b.pos)) < 0.24024 + 1e-9]
            self.assertEqual(len(touching), 3)

    def test_colours(self):
        self.assertEqual(tuple(self.w.balls[0].color), (230, 80, 60))
        self.assertEqual(tuple(self.w.balls[19].color), (250, 200, 60))
        self.assertEqual(tuple(self.w.balls[10].color), (237, 120, 60))

    def test_world(self):
        self.assertEqual((self.w.half_width, self.w.height, self.w.gravity, self.w.restitution),
                         (1.0, 3.0, -9.81, 0.9))
