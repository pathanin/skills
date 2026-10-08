import math


def _lerp(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


class Solid:
    def __init__(self, color):
        self.color = tuple(color)

    def sample(self, uv, point):
        return self.color


class Checker:
    """3D checker: cells of size `scale`; colour a where floor(x/s+1e-4)+floor(y/s+1e-4)+floor(z/s+1e-4) is even."""
    def __init__(self, scale, a, b):
        self.scale, self.a, self.b = float(scale), tuple(a), tuple(b)

    def sample(self, uv, point):
        n = sum(math.floor(c / self.scale + 1e-4) for c in point)
        return self.a if n % 2 == 0 else self.b


class Stripes:
    """Stripes along uv: colour a where floor(u * count) is even."""
    def __init__(self, count, a, b):
        self.count, self.a, self.b = int(count), tuple(a), tuple(b)

    def sample(self, uv, point):
        return self.a if math.floor(uv[0] * self.count) % 2 == 0 else self.b


def _hash(i, j, k, seed):
    h = math.sin(i * 127.1 + j * 311.7 + k * 74.7 + seed * 19.19) * 43758.5453
    return h - math.floor(h)


def _smooth(t):
    return t * t * (3 - 2 * t)


def value_noise(p, seed=0):
    """Trilinear value noise in [0, 1) on the integer lattice, smoothstep-interpolated."""
    i, j, k = (math.floor(c) for c in p)
    fx, fy, fz = (_smooth(p[0] - i), _smooth(p[1] - j), _smooth(p[2] - k))
    def h(a, b, c):
        return _hash(i + a, j + b, k + c, seed)
    x00 = h(0, 0, 0) + (h(1, 0, 0) - h(0, 0, 0)) * fx
    x10 = h(0, 1, 0) + (h(1, 1, 0) - h(0, 1, 0)) * fx
    x01 = h(0, 0, 1) + (h(1, 0, 1) - h(0, 0, 1)) * fx
    x11 = h(0, 1, 1) + (h(1, 1, 1) - h(0, 1, 1)) * fx
    y0 = x00 + (x10 - x00) * fy
    y1 = x01 + (x11 - x01) * fy
    return y0 + (y1 - y0) * fz


def fbm(p, octaves=4, seed=0):
    """Sum of octaves: value_noise(p * 2**o) / 2**o for o in 0..octaves-1, divided by the sum of weights."""
    total, norm = 0.0, 0.0
    for o in range(octaves):
        f = 2 ** o
        total += value_noise([p[0] * f, p[1] * f, p[2] * f], seed) / f
        norm += 1 / f
    return total / norm


class Noise:
    def __init__(self, scale, a, b, seed=0):
        self.scale, self.a, self.b, self.seed = float(scale), tuple(a), tuple(b), seed

    def sample(self, uv, point):
        p = [c * self.scale for c in point]
        return _lerp(self.a, self.b, fbm(p, 4, self.seed))


class Marble:
    """t = 0.5 + 0.5 * sin(scale * x + turbulence * 6.2832 * fbm(point * scale)); colour lerp(a, b, t)."""
    def __init__(self, scale, a, b, turbulence=1.0, seed=0):
        self.scale, self.a, self.b = float(scale), tuple(a), tuple(b)
        self.turbulence, self.seed = float(turbulence), seed

    def sample(self, uv, point):
        p = [c * self.scale for c in point]
        t = 0.5 + 0.5 * math.sin(p[0] + self.turbulence * 6.2832 * fbm(p, 4, self.seed))
        return _lerp(self.a, self.b, t)
