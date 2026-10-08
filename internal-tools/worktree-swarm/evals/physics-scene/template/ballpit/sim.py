"""Simulation loop and diagnostics. Provided; do not edit."""
import math

from ballpit import collide, integrate, walls
from ballpit.vec import dot, length, sub

COLLISION_PASSES = 4


def step(world, dt):
    integrate.advance(world, dt)
    walls.resolve(world)
    for _ in range(COLLISION_PASSES):
        collide.resolve(world)
    walls.resolve(world)


def energy(world):
    """Kinetic plus gravitational potential energy (floor = 0)."""
    return sum(0.5 * b.mass * dot(b.vel, b.vel) - b.mass * world.gravity * b.pos[1] for b in world.balls)


def max_penetration(world):
    """Deepest overlap between any ball and a wall, or between two balls (metres)."""
    worst = 0.0
    hw, h = world.half_width, world.height
    for b in world.balls:
        x, y, z = b.pos
        r = b.radius
        worst = max(worst, r - y, y + r - h, x + r - hw, -hw - (x - r), z + r - hw, -hw - (z - r))
    bs = world.balls
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            d = length(sub(bs[j].pos, bs[i].pos))
            worst = max(worst, bs[i].radius + bs[j].radius - d)
    return worst


def finite(world):
    return all(math.isfinite(v) for b in world.balls for v in b.pos + b.vel)
