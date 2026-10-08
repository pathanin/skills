import unittest

from ballpit.sheet import contact_sheet


def frame(c, w=3, h=2):
    return [[(c, c, c)] * w for _ in range(h)]


class TestSheet(unittest.TestCase):
    def test_layout(self):
        rows = contact_sheet([frame(k * 10) for k in range(1, 6)], cols=4, gutter=2, bg=(1, 2, 3))
        self.assertEqual(len(rows), 2 * 2 + 3 * 2)
        self.assertEqual(len(rows[0]), 4 * 3 + 5 * 2)
        self.assertEqual(rows[0][0], (1, 2, 3))
        self.assertEqual(rows[2][2], (10, 10, 10))
        self.assertEqual(rows[3][4], (10, 10, 10))
        self.assertEqual(rows[2][5], (1, 2, 3))
        self.assertEqual(rows[2][7], (20, 20, 20))
        self.assertEqual(rows[6][2], (50, 50, 50))
        self.assertEqual(rows[6][7], (1, 2, 3))    # unused cell

    def test_defaults(self):
        rows = contact_sheet([frame(9)] * 8)
        self.assertEqual((len(rows), len(rows[0])), (2 * 2 + 3 * 2, 4 * 3 + 5 * 2))
        self.assertEqual(rows[0][0], (16, 16, 16))
