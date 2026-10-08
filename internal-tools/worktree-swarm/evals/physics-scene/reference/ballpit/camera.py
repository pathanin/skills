import math

from ballpit.vec import add, cross, dot, mul, normalize, sub


class Camera:
    def __init__(self, eye, target, fov_deg, width, height, up=(0, 1, 0)):
        self.eye, self.width, self.height = list(eye), width, height
        self.forward = normalize(sub(target, eye))
        self.right = normalize(cross(self.forward, up))
        self.up = cross(self.right, self.forward)
        self.t = math.tan(math.radians(fov_deg) / 2)
        self.aspect = width / height

    def ray(self, px, py):
        sx = (2 * (px + 0.5) / self.width - 1) * self.t * self.aspect
        sy = (1 - 2 * (py + 0.5) / self.height) * self.t
        return self.eye, normalize(add(self.forward, add(mul(self.right, sx), mul(self.up, sy))))

    def project(self, point):
        d = sub(point, self.eye)
        z = dot(d, self.forward)
        if z <= 0:
            return None
        sx = dot(d, self.right) / z / (self.t * self.aspect)
        sy = dot(d, self.up) / z / self.t
        return (sx + 1) / 2 * self.width, (1 - sy) / 2 * self.height
