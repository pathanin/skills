"""Shared data model. CONTRACT v1: every module depends on these exact fields. Do not edit."""
from dataclasses import dataclass


@dataclass
class Ball:
    pos: list       # [x, y, z] in metres; y is up
    vel: list       # [vx, vy, vz] in m/s
    radius: float
    mass: float
    color: tuple    # (r, g, b), 0-255


@dataclass
class World:
    balls: list
    half_width: float = 1.0    # side walls at x = +-half_width and z = +-half_width
    height: float = 3.0        # floor at y = 0, ceiling at y = height
    gravity: float = -9.81     # acceleration along y
    restitution: float = 0.9   # used by walls and ball-ball collisions
