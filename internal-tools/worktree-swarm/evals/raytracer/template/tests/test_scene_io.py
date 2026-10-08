import json
import os
import tempfile
import unittest

from rt import scene_io
from rt.types import DirectionalLight, Material, PointLight

CALLS = []


def fake_factories():
    CALLS.clear()

    def shape(kind, many=1):
        def make(o, m, base):
            CALLS.append((kind, o, m, base))
            return [(kind, i, m) for i in range(many)] if many > 1 else (kind, m)
        return make

    def tex(kind):
        def make(t):
            CALLS.append((kind, t))
            return ("tex", kind)
        return make
    f = {k: shape(k) for k in ("sphere", "plane", "disk", "box", "triangle", "obj")}
    f.update({"icosphere": shape("icosphere", 3), "torus": shape("torus", 2), "cylinder": shape("cylinder", 4)})
    f.update({k: tex(k) for k in ("solid", "checker", "stripes", "noise", "marble")})
    f["camera"] = lambda o, w, h: ("camera", o["eye"], w, h)
    f["bvh"] = lambda objs: ("bvh", len(objs))
    return f


BASE = {
    "camera": {"eye": [0, 1, 5], "target": [0, 0, 0]},
    "materials": {
        "red": {"color": [1, 0, 0], "specular": 0.5},
        "shiny": {"extends": "red", "reflect": 0.4},
        "shinier": {"extends": "shiny", "color": [0, 1, 0], "shininess": 100},
        "floor": {"texture": {"type": "checker", "scale": 1, "a": [1, 1, 1], "b": [0, 0, 0]}},
    },
    "lights": [{"type": "point", "position": [1, 2, 3], "intensity": 5},
               {"type": "directional", "direction": [0, 1, 0], "color": [0.5, 0.5, 0.5]}],
    "objects": [{"type": "sphere", "center": [0, 0, 0], "radius": 1, "material": "shinier"},
                {"type": "plane", "point": [0, 0, 0], "normal": [0, 1, 0], "material": "floor"},
                {"type": "icosphere", "center": [0, 0, 0], "radius": 1},
                {"type": "cylinder", "base": [0, 0, 0], "radius": 1, "height": 1, "material": "red"}],
}


def build(data, **kw):
    return scene_io.build(json.loads(json.dumps(data)), 64, 48, kw.pop("base_dir", "/scenes"), fake_factories())


class TestSceneIO(unittest.TestCase):
    def test_build(self):
        s = build(BASE)
        self.assertEqual(s.camera, ("camera", [0, 1, 5], 64, 48))
        self.assertEqual(len(s.objects), 1 + 1 + 3 + 4)
        self.assertEqual(s.bvh, ("bvh", 9))
        self.assertEqual(s.meta, {"objects": 4, "primitives": 9})
        self.assertEqual(tuple(s.ambient), (0.05, 0.05, 0.05))
        self.assertEqual(s.max_depth, 4)

    def test_material_inheritance(self):
        build(BASE)
        m = CALLS[[c[0] for c in CALLS].index("sphere")][2]
        self.assertIsInstance(m, Material)
        self.assertEqual((tuple(m.color), m.specular, m.reflect, m.shininess), ((0, 1, 0), 0.5, 0.4, 100))
        floor = CALLS[[c[0] for c in CALLS].index("plane")][2]
        self.assertEqual(floor.texture, ("tex", "checker"))
        self.assertEqual(CALLS[[c[0] for c in CALLS].index("checker")][1]["scale"], 1)
        default = CALLS[[c[0] for c in CALLS].index("icosphere")][2]
        self.assertEqual(default, Material())

    def test_lights_and_options(self):
        data = dict(BASE, ambient=[0.1, 0.2, 0.3], max_depth=2,
                    background={"top": [0, 0, 1], "bottom": [1, 1, 1]})
        s = build(data)
        p, d = s.lights
        self.assertIsInstance(p, PointLight)
        self.assertEqual((list(p.position), tuple(p.color), p.intensity), ([1, 2, 3], (1, 1, 1), 5))
        self.assertIsInstance(d, DirectionalLight)
        self.assertEqual((tuple(d.color), d.intensity), ((0.5, 0.5, 0.5), 1.0))
        self.assertEqual((tuple(s.ambient), s.max_depth), ((0.1, 0.2, 0.3), 2))
        self.assertEqual((tuple(s.background_top), tuple(s.background_bottom)), ((0, 0, 1), (1, 1, 1)))

    def test_errors(self):
        bad = [dict(BASE, objects=[{"type": "sphere"}, {"type": "cone", "material": "red"}]),
               dict(BASE, objects=[{"type": "sphere", "material": "nope"}]),
               dict(BASE, materials={"a": {"extends": "b"}, "b": {"extends": "a"}}),
               dict(BASE, materials={"a": {"colour": [1, 0, 0]}}),
               dict(BASE, materials={"a": {"extends": "ghost"}}),
               dict(BASE, lights=[{"type": "spot"}])]
        for data in bad:
            with self.assertRaises(ValueError):
                build(data)
        with self.assertRaisesRegex(ValueError, "cone"):
            build(bad[0])
        with self.assertRaisesRegex(ValueError, "1"):
            build(bad[0])

    def test_load_passes_base_dir(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            with open(path, "w") as f:
                json.dump(dict(BASE, objects=[{"type": "obj", "path": "m.obj", "material": "red"}]), f)
            s = scene_io.load(path, 10, 8, fake_factories())
        kind, o, m, base = CALLS[-1]
        self.assertEqual((kind, o["path"], os.path.realpath(base)), ("obj", "m.obj", os.path.realpath(d)))
        self.assertEqual(s.camera[2:], (10, 8))
