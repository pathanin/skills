def advance(world, dt):
    for b in world.balls:
        b.vel[1] += world.gravity * dt
        for k in range(3):
            b.pos[k] += b.vel[k] * dt
