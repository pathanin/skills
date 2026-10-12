"""Tests for upscale.py. Run with the skill venv:
~/.cache/wallpaper-upscale/.venv/bin/python -m unittest discover -s <skill>/scripts -p 'test_*.py'
Uses model files from ~/.cache/wallpaper-upscale/models; a test whose model is missing is skipped."""
import os, subprocess, sys, tempfile, unittest
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.expanduser('~/.cache/wallpaper-upscale/models')
ESRGAN = f'{M}/RealESRGAN_x4plus_anime_6B.pth'                              # fp32, 4x
FDAT_XL = f'{M}/4x_IllustrationJaNai_V3detail_FDAT_XL_27k_bf16.safetensors'  # bf16, 4x
RCAN_2X = f'{M}/cand/2x-AnimeSharpV4_RCAN.safetensors'                       # 2x, module has .scale
FDAT_2X = f'{M}/cand/v3detail/2x_IllustrationJaNai_V3detail_FDAT_M_unshuffle_40k_fp16.safetensors'  # 2x, no .scale


def art(w, h):
    im = Image.new('RGB', (w, h), (230, 200, 210)); d = ImageDraw.Draw(im)
    for i in range(0, w, 13): d.line((i, 0, w - i, h), fill=(120, 30, 60), width=2)
    d.ellipse((w // 4, h // 4, 3 * w // 4, 3 * h // 4), outline=(30, 30, 120), width=3)
    return im


class Upscale(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def run_up(self, model, img, *args):
        src = os.path.join(self.tmp.name, 'in.png'); img.save(src)
        out = os.path.join(self.tmp.name, f'out{len(os.listdir(self.tmp.name))}.png')
        r = subprocess.run([sys.executable, f'{HERE}/upscale.py', model, src, out, *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return np.asarray(Image.open(out).convert('RGB')).astype(np.float32)

    @unittest.skipUnless(os.path.exists(RCAN_2X), '2x model not downloaded')
    def test_2x_model_gives_2x_output(self):
        o = self.run_up(RCAN_2X, art(40, 30))
        self.assertEqual(o.shape[:2], (60, 80))

    @unittest.skipUnless(os.path.exists(FDAT_2X), '2x FDAT model not downloaded')
    def test_2x_model_without_scale_attr(self):
        o = self.run_up(FDAT_2X, art(40, 30))
        self.assertEqual(o.shape[:2], (60, 80))

    @unittest.skipUnless(os.path.exists(FDAT_XL), 'FDAT-XL not downloaded')
    def test_half_precision_model_runs(self):
        o = self.run_up(FDAT_XL, art(40, 30))
        self.assertEqual(o.shape[:2], (120, 160))
        self.assertGreater(o.std(), 10)  # not a blank / NaN-collapsed image

    @unittest.skipUnless(os.path.exists(ESRGAN), 'anime_6B not downloaded')
    def test_small_tiles_have_no_seams(self):
        img = art(200, 150)
        whole = self.run_up(ESRGAN, img, '--tile', '512')
        tiled = self.run_up(ESRGAN, img, '--tile', '64')
        self.assertLess(np.abs(whole - tiled).max(), 3.0)


if __name__ == '__main__':
    unittest.main()
