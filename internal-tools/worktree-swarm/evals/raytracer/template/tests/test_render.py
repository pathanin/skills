import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests._support import read_png

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestRender(unittest.TestCase):
    def test_quick_render_matches_reference(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, os.path.join(ROOT, "render.py"), "--quick"], cwd=d, check=True,
                           capture_output=True, env={**os.environ, "PYTHONPATH": ROOT})
            with open(os.path.join(d, "out", "metrics.json")) as f:
                m = json.load(f)
            got = read_png(os.path.join(d, "out", "final.png"))
        self.assertEqual(m["primitives"], 1107)
        want = read_png(os.path.join(ROOT, "tests", "data", "quick_final.png"))
        self.assertEqual((len(got), len(got[0])), (len(want), len(want[0])))
        close = sum(1 for gr, wr in zip(got, want) for g, w in zip(gr, wr) if max(abs(a - b) for a, b in zip(g, w)) <= 8)
        self.assertGreaterEqual(close / (len(want) * len(want[0])), 0.97)
