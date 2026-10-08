import math

from rt.types import Hit
from rt.vec import dot, mul, neg, sub


class Sphere:
    def __init__(self, center, radius, material):
        self.center, self.radius, self.material = list(center), float(radius), material

    def intersect(self, ray, t_min, t_max):
        oc = sub(ray.origin, self.center)
        b = dot(oc, ray.direction)
        c = dot(oc, oc) - self.radius * self.radius
        disc = b * b - c
        if disc < 0:
            return None
        s = math.sqrt(disc)
        t = -b - s
        if not t_min < t < t_max:
            t = -b + s
            if not t_min < t < t_max:
                return None
        p = ray.at(t)
        outward = mul(sub(p, self.center), 1 / self.radius)
        front = dot(ray.direction, outward) < 0
        u = (math.atan2(-outward[2], outward[0]) + math.pi) / (2 * math.pi)
        v = math.acos(max(-1.0, min(1.0, -outward[1]))) / math.pi
        return Hit(t, p, outward if front else neg(outward), front, (u, v), self.material)

    def bounds(self):
        r = self.radius
        c = self.center
        return [c[0] - r, c[1] - r, c[2] - r], [c[0] + r, c[1] + r, c[2] + r]
