from ballpit.vec import add, dot, length, mul, sub


def resolve(world):
    e, bs = world.restitution, world.balls
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, b = bs[i], bs[j]
            delta = sub(b.pos, a.pos)
            d = length(delta)
            if d == 0 or d >= a.radius + b.radius:
                continue
            n = mul(delta, 1 / d)
            overlap = a.radius + b.radius - d
            tot = a.mass + b.mass
            a.pos = sub(a.pos, mul(n, overlap * b.mass / tot))
            b.pos = add(b.pos, mul(n, overlap * a.mass / tot))
            vrel = dot(sub(b.vel, a.vel), n)
            if vrel < 0:
                j_ = -(1 + e) * vrel / (1 / a.mass + 1 / b.mass)
                a.vel = sub(a.vel, mul(n, j_ / a.mass))
                b.vel = add(b.vel, mul(n, j_ / b.mass))
