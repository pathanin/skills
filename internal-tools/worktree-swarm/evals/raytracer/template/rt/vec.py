"""3-vectors as lists of floats. Provided; do not edit."""
import math


def add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def mul(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def hadamard(a, b):
    return [a[0] * b[0], a[1] * b[1], a[2] * b[2]]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    n = length(a)
    return [a[0] / n, a[1] / n, a[2] / n]


def neg(a):
    return [-a[0], -a[1], -a[2]]


def lerp(a, b, t):
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]


def reflect(d, n):
    """Reflect direction d about unit normal n."""
    return sub(d, mul(n, 2 * dot(d, n)))
