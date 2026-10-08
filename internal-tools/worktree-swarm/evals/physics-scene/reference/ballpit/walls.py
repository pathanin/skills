def resolve(world):
    hw, e = world.half_width, world.restitution
    for b in world.balls:
        r = b.radius
        for axis, lo, hi in ((0, -hw, hw), (1, 0.0, world.height), (2, -hw, hw)):
            if b.pos[axis] - r < lo:
                b.pos[axis] = lo + r
                if b.vel[axis] < 0:
                    b.vel[axis] = -e * b.vel[axis]
            elif b.pos[axis] + r > hi:
                b.pos[axis] = hi - r
                if b.vel[axis] > 0:
                    b.vel[axis] = -e * b.vel[axis]
