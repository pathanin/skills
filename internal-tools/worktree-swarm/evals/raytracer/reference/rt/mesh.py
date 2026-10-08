import math

from rt.shapes.triangle import Triangle
from rt.vec import add, mul, normalize

PHI = (1 + 5 ** 0.5) / 2
ICO_VERTS = [(-1, PHI, 0), (1, PHI, 0), (-1, -PHI, 0), (1, -PHI, 0), (0, -1, PHI), (0, 1, PHI),
             (0, -1, -PHI), (0, 1, -PHI), (PHI, 0, -1), (PHI, 0, 1), (-PHI, 0, -1), (-PHI, 0, 1)]
ICO_FACES = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
             (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]


def icosphere(center, radius, subdivisions, material):
    verts = [normalize(list(v)) for v in ICO_VERTS]
    faces = list(ICO_FACES)
    for _ in range(subdivisions):
        cache, new_faces = {}, []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache:
                verts.append(normalize(mul(add(verts[i], verts[j]), 0.5)))
                cache[key] = len(verts) - 1
            return cache[key]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new_faces
    pos = [add(center, mul(v, radius)) for v in verts]
    return [Triangle(pos[a], pos[b], pos[c], material, normals=[verts[a], verts[b], verts[c]])
            for a, b, c in faces]


def torus(center, major, minor, segments, rings, material):
    """Torus around the y axis. segments go around the main ring, rings around the tube."""
    def point(i, j):
        th = 2 * math.pi * (i % segments) / segments
        ph = 2 * math.pi * (j % rings) / rings
        n = [math.cos(ph) * math.cos(th), math.sin(ph), math.cos(ph) * math.sin(th)]
        p = [(major + minor * math.cos(ph)) * math.cos(th), minor * math.sin(ph),
             (major + minor * math.cos(ph)) * math.sin(th)]
        return add(center, p), n
    tris = []
    for i in range(segments):
        for j in range(rings):
            (p00, n00), (p10, n10) = point(i, j), point(i + 1, j)
            (p01, n01), (p11, n11) = point(i, j + 1), point(i + 1, j + 1)
            tris.append(Triangle(p00, p01, p11, material, normals=[n00, n01, n11]))
            tris.append(Triangle(p00, p11, p10, material, normals=[n00, n11, n10]))
    return tris


def cylinder(base, radius, height, segments, material, caps=True):
    """Upright cylinder from base (centre of the bottom cap) up the y axis."""
    tris = []
    top = add(base, [0.0, height, 0.0])
    for i in range(segments):
        a0, a1 = 2 * math.pi * i / segments, 2 * math.pi * (i + 1) / segments
        n0, n1 = [math.cos(a0), 0.0, math.sin(a0)], [math.cos(a1), 0.0, math.sin(a1)]
        b0, b1 = add(base, mul(n0, radius)), add(base, mul(n1, radius))
        t0, t1 = add(top, mul(n0, radius)), add(top, mul(n1, radius))
        tris.append(Triangle(b0, t0, t1, material, normals=[n0, n0, n1]))
        tris.append(Triangle(b0, t1, b1, material, normals=[n0, n1, n1]))
        if caps:
            tris.append(Triangle(top, t1, t0, material))
            tris.append(Triangle(base, b0, b1, material))
    return tris

