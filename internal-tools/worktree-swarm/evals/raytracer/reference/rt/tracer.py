import math

from rt import lighting
from rt.types import Ray
from rt.vec import add, dot, mul, neg, reflect

BIAS = 1e-4


def background(scene, direction):
    t = 0.5 * (direction[1] + 1.0)
    b, a = scene.background_top, scene.background_bottom
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def schlick(cos_i, ior):
    r0 = ((1 - ior) / (1 + ior)) ** 2
    return r0 + (1 - r0) * (1 - cos_i) ** 5


def trace(ray, scene, depth=0):
    hit = scene.bvh.intersect(ray, BIAS, math.inf)
    if hit is None:
        return background(scene, ray.direction)
    m, n, d = hit.material, hit.normal, ray.direction

    def occluded(o, direction, max_t):
        limit = max_t - BIAS if max_t != math.inf else math.inf
        return scene.bvh.intersect(Ray(o, direction), BIAS, limit) is not None

    local = lighting.shade(hit, neg(d), scene.lights, scene.ambient, occluded)
    kr, kt = m.reflect, m.transparency
    color = [c * (1 - kr - kt) for c in local]
    if depth >= scene.max_depth:
        return tuple(color)
    if kr > 0:
        r = trace(Ray(add(hit.point, mul(n, BIAS)), reflect(d, n)), scene, depth + 1)
        color = [color[k] + kr * r[k] for k in range(3)]
    if kt > 0:
        eta = 1 / m.ior if hit.front_face else m.ior
        cos_i = min(1.0, -dot(d, n))
        sin2_t = eta * eta * (1 - cos_i * cos_i)
        refl = trace(Ray(add(hit.point, mul(n, BIAS)), reflect(d, n)), scene, depth + 1)
        if sin2_t > 1:
            mix = refl
        else:
            t_dir = add(mul(d, eta), mul(n, eta * cos_i - math.sqrt(1 - sin2_t)))
            refr = trace(Ray(add(hit.point, mul(n, -BIAS)), t_dir), scene, depth + 1)
            f = schlick(cos_i, m.ior)
            mix = [(1 - f) * refr[k] + f * refl[k] for k in range(3)]
        color = [color[k] + kt * mix[k] for k in range(3)]
    return tuple(color)
