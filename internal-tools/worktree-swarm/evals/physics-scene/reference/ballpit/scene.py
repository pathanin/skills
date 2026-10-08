import math

from ballpit.world import Ball, World

BOTTOM, TOP = (230, 80, 60), (250, 200, 60)


def pyramid(layers=4):
    r = 0.12
    d = 2 * r * 1.001
    balls = []
    for k in range(layers):
        n = layers - k
        pts = [((j - i / 2) * d, i * d * math.sqrt(3) / 2) for i in range(n) for j in range(i + 1)]
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        y = r * 1.001 + k * d * math.sqrt(2 / 3)
        f = k / (layers - 1) if layers > 1 else 0
        color = tuple(round(BOTTOM[c] + (TOP[c] - BOTTOM[c]) * f) for c in range(3))
        for x, z in pts:
            balls.append(Ball([x - cx, y, z - cz], [0.0, 0.0, 0.0], r, 1.0, color))
    balls.append(Ball([-0.85, 0.3, 0.02], [6.0, 0.6, 0.0], 0.12, 2.0, (240, 240, 240)))
    return World(balls, half_width=1.0, height=3.0, gravity=-9.81, restitution=0.9)
