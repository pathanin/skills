from rt.types import Hit
from rt.vec import add, cross, dot, mul, neg, normalize, sub

EPS = 1e-9


class Triangle:
    def __init__(self, a, b, c, material, normals=None):
        self.a, self.b, self.c = list(a), list(b), list(c)
        self.material = material
        self.e1, self.e2 = sub(self.b, self.a), sub(self.c, self.a)
        self.geo_normal = normalize(cross(self.e1, self.e2))
        self.normals = [normalize(n) for n in normals] if normals else None

    def intersect(self, ray, t_min, t_max):
        d = ray.direction
        p = cross(d, self.e2)
        det = dot(self.e1, p)
        if abs(det) < EPS:
            return None
        inv = 1.0 / det
        s = sub(ray.origin, self.a)
        u = dot(s, p) * inv
        if u < 0.0 or u > 1.0:
            return None
        q = cross(s, self.e1)
        v = dot(d, q) * inv
        if v < 0.0 or u + v > 1.0:
            return None
        t = dot(self.e2, q) * inv
        if not t_min < t < t_max:
            return None
        front = dot(d, self.geo_normal) < 0
        if self.normals:
            w = 1.0 - u - v
            na, nb, nc = self.normals
            n = normalize(add(add(mul(na, w), mul(nb, u)), mul(nc, v)))
        else:
            n = self.geo_normal
        if not front:
            n = neg(n)
        return Hit(t, ray.at(t), n, front, (u, v), self.material)

    def bounds(self):
        pts = (self.a, self.b, self.c)
        return [min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]
