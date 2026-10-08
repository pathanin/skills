from rt.types import Hit


class Box:
    def __init__(self, lo, hi, material):
        self.lo = [min(a, b) for a, b in zip(lo, hi)]
        self.hi = [max(a, b) for a, b in zip(lo, hi)]
        self.material = material

    def intersect(self, ray, t_min, t_max):
        o, d = ray.origin, ray.direction
        t_near, t_far = -float("inf"), float("inf")
        near_axis = far_axis = 0
        near_sign = far_sign = 1.0
        for k in range(3):
            if abs(d[k]) < 1e-12:
                if o[k] < self.lo[k] or o[k] > self.hi[k]:
                    return None
                continue
            t1 = (self.lo[k] - o[k]) / d[k]
            t2 = (self.hi[k] - o[k]) / d[k]
            s1, s2 = -1.0, 1.0              # outward normal sign of the lo / hi face
            if t1 > t2:
                t1, t2, s1, s2 = t2, t1, s2, s1
            if t1 > t_near:
                t_near, near_axis, near_sign = t1, k, s1
            if t2 < t_far:
                t_far, far_axis, far_sign = t2, k, s2
            if t_near > t_far:
                return None
        if t_min < t_near < t_max:
            t, axis, sign, front = t_near, near_axis, near_sign, True
        elif t_min < t_far < t_max:
            t, axis, sign, front = t_far, far_axis, far_sign, False
        else:
            return None
        p = ray.at(t)
        normal = [0.0, 0.0, 0.0]
        normal[axis] = sign if front else -sign
        a, b = [k for k in range(3) if k != axis]
        u = (p[a] - self.lo[a]) / (self.hi[a] - self.lo[a])
        v = (p[b] - self.lo[b]) / (self.hi[b] - self.lo[b])
        return Hit(t, p, normal, front, (u, v), self.material)

    def bounds(self):
        return list(self.lo), list(self.hi)
