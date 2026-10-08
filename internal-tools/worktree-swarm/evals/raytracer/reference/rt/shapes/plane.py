from rt.types import Hit
from rt.vec import cross, dot, length, neg, normalize, sub


def _tangents(n):
    a = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
    tu = normalize(cross(n, a))
    return tu, cross(n, tu)


class Plane:
    def __init__(self, point, normal, material):
        self.point, self.normal, self.material = list(point), normalize(normal), material
        self.tu, self.tv = _tangents(self.normal)

    def _hit(self, ray, t_min, t_max):
        denom = dot(self.normal, ray.direction)
        if abs(denom) < 1e-9:
            return None
        t = dot(sub(self.point, ray.origin), self.normal) / denom
        if not t_min < t < t_max:
            return None
        return t

    def intersect(self, ray, t_min, t_max):
        t = self._hit(ray, t_min, t_max)
        if t is None:
            return None
        p = ray.at(t)
        rel = sub(p, self.point)
        front = dot(ray.direction, self.normal) < 0
        return Hit(t, p, self.normal if front else neg(self.normal), front,
                   (dot(rel, self.tu), dot(rel, self.tv)), self.material)

    def bounds(self):
        return None


class Disk(Plane):
    def __init__(self, center, normal, radius, material):
        super().__init__(center, normal, material)
        self.radius = float(radius)

    def intersect(self, ray, t_min, t_max):
        t = self._hit(ray, t_min, t_max)
        if t is None:
            return None
        p = ray.at(t)
        rel = sub(p, self.point)
        if length(rel) > self.radius:
            return None
        front = dot(ray.direction, self.normal) < 0
        u = 0.5 + dot(rel, self.tu) / (2 * self.radius)
        v = 0.5 + dot(rel, self.tv) / (2 * self.radius)
        return Hit(t, p, self.normal if front else neg(self.normal), front, (u, v), self.material)

    def bounds(self):
        r = self.radius
        ext = [r * (1 - self.normal[k] ** 2) ** 0.5 for k in range(3)]
        c = self.point
        return [c[k] - ext[k] for k in range(3)], [c[k] + ext[k] for k in range(3)]
