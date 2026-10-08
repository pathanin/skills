import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMovie(unittest.TestCase):
    def test_quick_movie_physics(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, os.path.join(ROOT, "make_movie.py"), "--quick"], cwd=d, check=True,
                           capture_output=True, env={**os.environ, "PYTHONPATH": ROOT})
            with open(os.path.join(d, "out", "metrics.json")) as f:
                m = json.load(f)
            for f in ("sheet.png", "final.png"):
                self.assertTrue(os.path.getsize(os.path.join(d, "out", f)) > 100)
        self.assertEqual(m["balls"], 21)
        self.assertTrue(m["finite"])
        self.assertLessEqual(m["energy_max_ratio"], 1.02)
        self.assertLess(m["energy_end"], m["energy_start"])
        self.assertLessEqual(m["max_penetration"], 0.03)
