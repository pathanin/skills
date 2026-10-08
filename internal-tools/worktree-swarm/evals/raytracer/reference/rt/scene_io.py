import json
import os

from rt.types import DirectionalLight, Material, PointLight, Scene

MATERIAL_FIELDS = ("color", "diffuse", "specular", "shininess", "reflect", "transparency", "ior")


def default_factories():
    from rt import bvh, mesh, obj, textures
    from rt.camera import Camera
    from rt.shapes.box import Box
    from rt.shapes.plane import Disk, Plane
    from rt.shapes.sphere import Sphere
    from rt.shapes.triangle import Triangle
    return {
        "camera": lambda o, w, h: Camera(o["eye"], o["target"], o.get("up", [0, 1, 0]), o.get("vfov", 40), w, h),
        "bvh": lambda shapes: bvh.build(shapes),
        "sphere": lambda o, m, base: Sphere(o["center"], o["radius"], m),
        "plane": lambda o, m, base: Plane(o["point"], o["normal"], m),
        "disk": lambda o, m, base: Disk(o["center"], o["normal"], o["radius"], m),
        "box": lambda o, m, base: Box(o["min"], o["max"], m),
        "triangle": lambda o, m, base: Triangle(o["a"], o["b"], o["c"], m),
        "icosphere": lambda o, m, base: mesh.icosphere(o["center"], o["radius"], o.get("subdivisions", 2), m),
        "torus": lambda o, m, base: mesh.torus(o["center"], o["major"], o["minor"], o.get("segments", 32),
                                               o.get("rings", 16), m),
        "cylinder": lambda o, m, base: mesh.cylinder(o["base"], o["radius"], o["height"], o.get("segments", 24), m,
                                                     o.get("caps", True)),
        "obj": lambda o, m, base: obj.load(os.path.join(base, o["path"]), m, o.get("scale", 1.0),
                                           o.get("offset", [0, 0, 0])),
        "solid": lambda t: textures.Solid(t["color"]),
        "checker": lambda t: textures.Checker(t["scale"], t["a"], t["b"]),
        "stripes": lambda t: textures.Stripes(t["count"], t["a"], t["b"]),
        "noise": lambda t: textures.Noise(t["scale"], t["a"], t["b"], t.get("seed", 0)),
        "marble": lambda t: textures.Marble(t["scale"], t["a"], t["b"], t.get("turbulence", 1.0), t.get("seed", 0)),
    }


def _materials(specs, factories):
    resolved = {}

    def resolve(name, stack):
        if name in resolved:
            return resolved[name]
        if name not in specs:
            raise ValueError(f"unknown material {name!r}")
        if name in stack:
            raise ValueError(f"material {name!r} extends itself")
        spec = dict(specs[name])
        parent = spec.pop("extends", None)
        fields = dict(resolve(parent, stack + [name])) if parent else {}
        for k, v in spec.items():
            if k != "texture" and k not in MATERIAL_FIELDS:
                raise ValueError(f"material {name!r}: unknown field {k!r}")
            fields[k] = v
        resolved[name] = fields
        return fields

    out = {}
    for name in specs:
        fields = dict(resolve(name, []))
        tex = fields.pop("texture", None)
        if "color" in fields:
            fields["color"] = tuple(fields["color"])
        if tex is not None:
            if tex.get("type") not in factories or tex["type"] in ("camera", "bvh"):
                raise ValueError(f"material {name!r}: unknown texture type {tex.get('type')!r}")
            fields["texture"] = factories[tex["type"]](tex)
        out[name] = Material(**fields)
    return out


def build(data, width, height, base_dir=".", factories=None):
    f = factories or default_factories()
    materials = _materials(data.get("materials", {}), f)
    lights = []
    for i, l in enumerate(data.get("lights", [])):
        if l.get("type") == "point":
            lights.append(PointLight(list(l["position"]), tuple(l.get("color", (1, 1, 1))), l.get("intensity", 1.0)))
        elif l.get("type") == "directional":
            lights.append(DirectionalLight(list(l["direction"]), tuple(l.get("color", (1, 1, 1))),
                                           l.get("intensity", 1.0)))
        else:
            raise ValueError(f"light {i}: unknown type {l.get('type')!r}")
    objects = []
    for i, o in enumerate(data.get("objects", [])):
        kind = o.get("type")
        if kind not in f or kind in ("camera", "bvh", "solid", "checker", "stripes", "noise", "marble"):
            raise ValueError(f"object {i}: unknown type {kind!r}")
        mat_name = o.get("material", "default")
        if mat_name not in materials:
            if mat_name != "default":
                raise ValueError(f"object {i}: unknown material {mat_name!r}")
            materials["default"] = Material()
        made = f[kind](o, materials[mat_name], base_dir)
        objects.extend(made if isinstance(made, list) else [made])
    scene = Scene(camera=f["camera"](data["camera"], width, height), lights=lights,
                  ambient=tuple(data.get("ambient", (0.05, 0.05, 0.05))), objects=objects, bvh=f["bvh"](objects))
    if "background" in data:
        scene.background_top = tuple(data["background"]["top"])
        scene.background_bottom = tuple(data["background"]["bottom"])
    scene.max_depth = data.get("max_depth", scene.max_depth)
    scene.meta = {"objects": len(data.get("objects", [])), "primitives": len(objects)}
    return scene


def load(path, width, height, factories=None):
    with open(path) as fh:
        data = json.load(fh)
    return build(data, width, height, os.path.dirname(os.path.abspath(path)), factories)
