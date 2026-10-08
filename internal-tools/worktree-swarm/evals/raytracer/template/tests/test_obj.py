import os
import tempfile
import unittest

from tests._support import ensure_triangle

ensure_triangle()
from rt import obj  # noqa: E402
from rt.types import Material  # noqa: E402

M = Material()
QUAD = """# a unit quad and a triangle
o thing
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
vt 0 0
vn 0 0 1
s off
f 1 2 3 4
f -4//1 -3//1 -2//1
f 1/1/1 2/1/1 4/1
"""


class TestObj(unittest.TestCase):
    def test_parse(self):
        tris = obj.parse(QUAD, M)
        self.assertEqual(len(tris), 4)
        self.assertEqual([tris[0].a, tris[0].b, tris[0].c], [[0, 0, 0], [1, 0, 0], [1, 1, 0]])
        self.assertEqual([tris[1].a, tris[1].b, tris[1].c], [[0, 0, 0], [1, 1, 0], [0, 1, 0]])
        self.assertIsNone(tris[0].normals)
        self.assertEqual([list(n) for n in tris[2].normals], [[0, 0, 1]] * 3)
        self.assertEqual(tris[2].a, [0, 0, 0])
        self.assertIsNone(tris[3].normals)    # one corner has no normal
        self.assertIs(tris[0].material, M)

    def test_scale_offset(self):
        tris = obj.parse("v 1 2 3\nv 2 2 3\nv 1 3 3\nf 1 2 3\n", M, scale=2.0, offset=(1, 0, -1))
        self.assertEqual(tris[0].a, [3.0, 4.0, 5.0])
        self.assertEqual(tris[0].c, [3.0, 6.0, 5.0])

    def test_errors_name_the_line(self):
        with self.assertRaisesRegex(ValueError, "3"):
            obj.parse("v 0 0 0\nv 1 0 0\nf 1 2\n", M)
        with self.assertRaisesRegex(ValueError, "4"):
            obj.parse("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 9\n", M)

    def test_load_and_gem(self):
        with tempfile.NamedTemporaryFile("w", suffix=".obj", delete=False) as f:
            f.write(QUAD)
        try:
            self.assertEqual(len(obj.load(f.name, M)), 4)
        finally:
            os.unlink(f.name)
        gem = obj.load(os.path.join(os.path.dirname(__file__), "..", "assets", "gem.obj"), M)
        self.assertEqual(len(gem), 6 + 16 + 8)
