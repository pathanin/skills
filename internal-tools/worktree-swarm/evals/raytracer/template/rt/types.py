"""Shared data model. CONTRACT v1: every module depends on these exact names and fields. Do not edit.

Colors are linear RGB floats (0..1 for surfaces, unbounded for light). Directions are unit 3-vectors.

Shape protocol (every class in rt/shapes/ and every Triangle):
    shape.material                                   -> Material
    shape.intersect(ray, t_min, t_max) -> Hit | None   nearest hit with t_min < t < t_max
    shape.bounds() -> (lo, hi) | None                  axis-aligned box; None if unbounded

Texture protocol (every class in rt/textures.py):
    texture.sample(uv, point) -> (r, g, b)
"""
from dataclasses import dataclass, field


@dataclass
class Ray:
    origin: list
    direction: list          # unit length

    def at(self, t):
        o, d = self.origin, self.direction
        return [o[0] + d[0] * t, o[1] + d[1] * t, o[2] + d[2] * t]


@dataclass
class Material:
    color: tuple = (0.8, 0.8, 0.8)
    texture: object = None   # when set, texture.sample(hit.uv, hit.point) replaces color
    diffuse: float = 0.9
    specular: float = 0.0
    shininess: float = 32.0
    reflect: float = 0.0      # share of mirror reflection, 0..1
    transparency: float = 0.0  # share of refraction, 0..1
    ior: float = 1.5


@dataclass
class Hit:
    t: float
    point: list
    normal: list             # unit shading normal, always facing against the ray
    front_face: bool         # True when the ray hits the outside of the surface
    uv: tuple
    material: Material


@dataclass
class PointLight:
    position: list
    color: tuple = (1.0, 1.0, 1.0)
    intensity: float = 1.0


@dataclass
class DirectionalLight:
    direction: list          # unit vector pointing TOWARDS the light
    color: tuple = (1.0, 1.0, 1.0)
    intensity: float = 1.0


@dataclass
class Scene:
    camera: object
    lights: list
    ambient: tuple
    objects: list
    bvh: object              # has .intersect(ray, t_min, t_max) -> Hit | None
    background_top: tuple = (0.45, 0.62, 0.95)
    background_bottom: tuple = (0.95, 0.95, 1.0)
    max_depth: int = 4
    meta: dict = field(default_factory=dict)
