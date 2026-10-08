import math

from rt.types import Ray
from rt.vec import add, cross, mul, normalize, sub


class Camera:
    def __init__(self, eye, target, up, vfov, width, height):
        self.eye, self.width, self.height = list(eye), int(width), int(height)
        self.forward = normalize(sub(target, eye))
        self.right = normalize(cross(self.forward, up))
        self.up = cross(self.right, self.forward)
        self.half_h = math.tan(math.radians(vfov) / 2)
        self.half_w = self.half_h * self.width / self.height

    def ray(self, px, py, sx=0.5, sy=0.5):
        """Ray through point (px + sx, py + sy) of the image; row 0 is the top."""
        x = (2 * (px + sx) / self.width - 1) * self.half_w
        y = (1 - 2 * (py + sy) / self.height) * self.half_h
        d = normalize(add(self.forward, add(mul(self.right, x), mul(self.up, y))))
        return Ray(list(self.eye), d)

    @classmethod
    def orbit(cls, target, distance, height, angle_deg, vfov, width, height_px):
        """Camera circling target at the given horizontal distance and height, looking at target."""
        a = math.radians(angle_deg)
        eye = [target[0] + distance * math.sin(a), target[1] + height, target[2] + distance * math.cos(a)]
        return cls(eye, target, (0.0, 1.0, 0.0), vfov, width, height_px)
