import math

from ballpit.vec import add, dot, mul, normalize, sub

L = normalize([-0.4, 1.0, 0.3])
TOP, BOTTOM = (30, 34, 48), (70, 76, 96)


def _hit_sphere(o, d, b):
    oc = sub(o, b.pos)
    bq = dot(oc, d)
    c = dot(oc, oc) - b.radius * b.radius
    disc = bq * bq - c
    if disc < 0:
        return None
    s = math.sqrt(disc)
    for t in (-bq - s, -bq + s):
        if t > 1e-6:
            return t
    return None


def _shadowed(p, balls):
    return any(_hit_sphere(p, L, b) is not None for b in balls)


def _px(c):
    return tuple(max(0, min(255, round(v))) for v in c)


def render(world, camera):
    rows = []
    for py in range(camera.height):
        f = py / (camera.height - 1) if camera.height > 1 else 0
        bg = _px([TOP[k] + (BOTTOM[k] - TOP[k]) * f for k in range(3)])
        row = []
        for px in range(camera.width):
            o, d = camera.ray(px, py)
            best, ball = None, None
            for b in world.balls:
                t = _hit_sphere(o, d, b)
                if t is not None and (best is None or t < best):
                    best, ball = t, b
            if ball is not None:
                p = add(o, mul(d, best))
                n = normalize(sub(p, ball.pos))
                lit = 0 if _shadowed(add(p, mul(n, 1e-4)), world.balls) else max(0.0, dot(n, L))
                row.append(_px(mul(ball.color, 0.25 + 0.75 * lit)))
                continue
            if d[1] < 0:
                t = -o[1] / d[1]
                p = add(o, mul(d, t))
                if abs(p[0]) <= world.half_width and abs(p[2]) <= world.half_width:
                    base = 200 if (math.floor(p[0] / 0.25) + math.floor(p[2] / 0.25)) % 2 == 0 else 120
                    lit = 0 if _shadowed(add(p, [0, 1e-4, 0]), world.balls) else L[1]
                    row.append(_px([base * (0.25 + 0.75 * lit)] * 3))
                    continue
            row.append(bg)
        rows.append(row)
    return rows
