from rt.shapes.triangle import Triangle


def _index(token, count):
    i = int(token)
    return i - 1 if i > 0 else count + i


def parse(text, material, scale=1.0, offset=(0.0, 0.0, 0.0)):
    """Wavefront OBJ text -> list of Triangle. Supports v, vn and f (v, v/vt, v//vn, v/vt/vn,
    negative indices, polygons fan-triangulated). Everything else is ignored."""
    verts, normals, tris = [], [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        tag, args = parts[0], parts[1:]
        if tag == "v":
            x, y, z = (float(a) for a in args[:3])
            verts.append([x * scale + offset[0], y * scale + offset[1], z * scale + offset[2]])
        elif tag == "vn":
            normals.append([float(a) for a in args[:3]])
        elif tag == "f":
            if len(args) < 3:
                raise ValueError(f"line {lineno}: face needs at least 3 vertices")
            corners = []
            for a in args:
                fields = a.split("/")
                vi = _index(fields[0], len(verts))
                ni = _index(fields[2], len(normals)) if len(fields) == 3 and fields[2] else None
                if not 0 <= vi < len(verts) or (ni is not None and not 0 <= ni < len(normals)):
                    raise ValueError(f"line {lineno}: index out of range")
                corners.append((vi, ni))
            for k in range(1, len(corners) - 1):
                c = (corners[0], corners[k], corners[k + 1])
                ns = [normals[ni] for _, ni in c] if all(ni is not None for _, ni in c) else None
                tris.append(Triangle(verts[c[0][0]], verts[c[1][0]], verts[c[2][0]], material, normals=ns))
    return tris


def load(path, material, scale=1.0, offset=(0.0, 0.0, 0.0)):
    with open(path) as f:
        return parse(f.read(), material, scale, offset)
