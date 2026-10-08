"""Test helpers. Provided; do not edit."""
import importlib
import math
import struct
import sys
import types
import zlib

from rt.vec import cross, normalize, sub


def ensure_module(name, attrs):
    """Import `name`; if it doesn't exist yet (another piece builds it), install a stub with `attrs`."""
    try:
        return importlib.import_module(name)
    except ImportError:
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        mod.__stub__ = True
        sys.modules[name] = mod
        return mod


class StubTriangle:
    """Records constructor args the way rt.shapes.triangle.Triangle stores them."""
    def __init__(self, a, b, c, material, normals=None):
        self.a, self.b, self.c, self.material = list(a), list(b), list(c), material
        self.geo_normal = normalize(cross(sub(self.b, self.a), sub(self.c, self.a)))
        self.normals = [normalize(n) for n in normals] if normals else None


def ensure_triangle():
    return ensure_module("rt.shapes.triangle", {"Triangle": StubTriangle}).Triangle


def read_png(path):
    """Decode the 8-bit RGB, filter-0 PNGs that rt.png writes."""
    data = open(path, "rb").read()
    pos, idat, w = 8, b"", None
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = 1 + 3 * w
    return [[tuple(raw[y * stride + 1 + 3 * x: y * stride + 4 + 3 * x]) for x in range(w)] for y in range(h)]


def close(a, b, places=6):
    return all(math.isclose(x, y, abs_tol=10 ** -places) for x, y in zip(a, b))
