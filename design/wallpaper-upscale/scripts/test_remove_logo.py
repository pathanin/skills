"""Tests for remove_logo.py. Run with the skill venv:
~/.cache/wallpaper-upscale/.venv/bin/python -m unittest discover -s <skill>/scripts -p 'test_*.py'
The end-to-end LaMa test is skipped if ~/.cache/wallpaper-upscale/models/lama/big-lama.pt is missing."""
import os, subprocess, sys, tempfile, unittest
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import remove_logo as rl

LAMA = os.path.expanduser('~/.cache/wallpaper-upscale/models/lama/big-lama.pt')


def background(w, h):
    """Dark diagonal gradient with soft texture - something an inpainter can continue."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 40 + 50 * (x + y) / (w + h) + 6 * np.sin(x / 9) * np.cos(y / 11)
    return np.dstack([v, v * 0.9, v * 1.1]).clip(0, 255).astype(np.uint8)


class Mask(unittest.TestCase):
    def test_parse_box_with_and_without_threshold(self):
        self.assertEqual(rl.parse_box('1,2,30,40'), (1, 2, 30, 40, None))
        self.assertEqual(rl.parse_box('1,2,30,40:65'), (1, 2, 30, 40, 65))

    def test_white_and_orange_inside_box_only(self):
        a = background(200, 100)
        a[20:40, 20:40] = 255                 # white logo part, inside box
        a[20:40, 50:60] = (40, 90, 230)       # orange (BGR) logo part, inside box
        a[20:40, 150:170] = 255               # white art outside the box
        m = rl.build_mask(a, [(10, 10, 100, 60, None)], thresh=150, grow=1)
        self.assertTrue(m[30, 30] and m[30, 55])
        self.assertFalse(m[30, 160])          # outside box: kept
        self.assertFalse(m[80, 30])           # dark background: kept

    def test_per_box_threshold_catches_faint_grey(self):
        a = background(100, 60)
        a[10:50, 30:32] = 110                 # faint grey separator line
        self.assertFalse(rl.build_mask(a, [(20, 5, 40, 55, None)], 150, 1)[30, 31])
        self.assertTrue(rl.build_mask(a, [(20, 5, 40, 55, 65)], 150, 1)[30, 31])

    def test_grow_covers_halo_but_not_beyond(self):
        a = np.zeros((60, 60, 3), np.uint8); a[25:35, 25:35] = 255
        m = rl.build_mask(a, [(0, 0, 60, 60, None)], 150, grow=7)   # radius 3
        self.assertTrue(m[30, 37])            # 3 px outside the logo edge (34)
        self.assertFalse(m[30, 39])           # 5 px outside


class Inpaint(unittest.TestCase):
    def test_pads_to_multiple_of_8_and_only_changes_masked_pixels(self):
        seen = {}
        def fake_net(img, mask):
            seen['img'], seen['mask'] = tuple(img.shape), mask
            return torch.ones_like(img) * 0.5
        import torch
        a = background(101, 67)
        m = np.zeros(a.shape[:2], np.uint8); m[20:30, 40:60] = 255
        out = rl.inpaint_lama(a, m, fake_net)
        self.assertEqual(seen['img'][2] % 8, 0); self.assertEqual(seen['img'][3] % 8, 0)
        self.assertEqual(set(seen['mask'].unique().tolist()), {0.0, 1.0})
        self.assertEqual(out.shape, a.shape)
        self.assertTrue(np.array_equal(out[m == 0], a[m == 0]))
        self.assertTrue(np.all(np.abs(out[m > 0].astype(int) - 128) <= 1))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.bg = background(320, 192)
        a = self.bg.copy(); cv2.putText(a, 'LOGO', (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 6)
        self.src, self.out = os.path.join(self.tmp.name, 'in.png'), os.path.join(self.tmp.name, 'out.png')
        cv2.imwrite(self.src, a)

    def run_cli(self, *extra):
        r = subprocess.run([sys.executable, f'{HERE}/remove_logo.py', self.src, self.out, '20,50,260,150', *extra],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return cv2.imread(self.out), cv2.imread(self.out[:-4] + '_mask.png', 0)

    def check(self, out, m, tol):
        self.assertGreater((m > 0).sum(), 2000)                       # logo actually masked
        err = np.abs(out.astype(int) - self.bg.astype(int))
        self.assertLess(err[m > 0].mean(), tol)                       # logo gone, background restored
        self.assertTrue(np.array_equal(out[m == 0], cv2.imread(self.src)[m == 0]))

    @unittest.skipUnless(os.path.exists(LAMA), 'big-lama.pt not downloaded')
    def test_lama_removes_logo(self):
        self.check(*self.run_cli(), tol=12)

    def test_telea_fallback_runs_without_model(self):
        self.check(*self.run_cli('--telea', '--model', '/nonexistent.pt'), tol=20)

    def test_missing_model_is_an_error_not_a_silent_fallback(self):
        r = subprocess.run([sys.executable, f'{HERE}/remove_logo.py', self.src, self.out, '20,50,260,150',
                            '--model', '/nonexistent.pt'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('big-lama.pt', r.stderr + r.stdout)
        self.assertFalse(os.path.exists(self.out))


if __name__ == '__main__':
    unittest.main()
