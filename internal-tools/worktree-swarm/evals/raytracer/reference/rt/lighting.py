import math

from rt.types import PointLight
from rt.vec import add, dot, length, mul, normalize, sub

SHADOW_BIAS = 1e-4


def surface_color(hit):
    m = hit.material
    return tuple(m.texture.sample(hit.uv, hit.point)) if m.texture is not None else tuple(m.color)


def shade(hit, view_dir, lights, ambient, occluded):
    """Blinn-Phong. view_dir points from the surface towards the viewer.
    occluded(origin, direction, max_t) -> bool says whether something blocks a shadow ray."""
    base = surface_color(hit)
    m, n, p = hit.material, hit.normal, hit.point
    out = [ambient[k] * base[k] for k in range(3)]
    origin = add(p, mul(n, SHADOW_BIAS))
    for light in lights:
        if isinstance(light, PointLight):
            to = sub(light.position, p)
            dist = length(to)
            l_dir = mul(to, 1 / dist)
            radiance = [c * light.intensity / (dist * dist) for c in light.color]
        else:
            l_dir = normalize(light.direction)
            dist = math.inf
            radiance = [c * light.intensity for c in light.color]
        ndl = dot(n, l_dir)
        if ndl <= 0:
            continue
        if occluded(origin, l_dir, dist):
            continue
        h = normalize(add(l_dir, view_dir))
        spec = m.specular * max(0.0, dot(n, h)) ** m.shininess
        for k in range(3):
            out[k] += radiance[k] * (m.diffuse * base[k] * ndl + spec)
    return tuple(out)
