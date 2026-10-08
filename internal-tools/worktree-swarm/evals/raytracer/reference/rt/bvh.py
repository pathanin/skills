INF = float("inf")


class _Node:
    __slots__ = ("lo", "hi", "left", "right", "shapes")

    def __init__(self, lo, hi, left=None, right=None, shapes=None):
        self.lo, self.hi, self.left, self.right, self.shapes = lo, hi, left, right, shapes


def _box_hit(lo, hi, o, inv, t_min, t_max):
    for k in range(3):
        t1 = (lo[k] - o[k]) * inv[k]
        t2 = (hi[k] - o[k]) * inv[k]
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > t_min:
            t_min = t1
        if t2 < t_max:
            t_max = t2
        if t_min > t_max:
            return False
    return True


def _build(items, leaf_size):
    lo = [min(b[0][k] for b, _ in items) for k in range(3)]
    hi = [max(b[1][k] for b, _ in items) for k in range(3)]
    if len(items) <= leaf_size:
        return _Node(lo, hi, shapes=[s for _, s in items])
    cent = [[(b[0][k] + b[1][k]) / 2 for k in range(3)] for b, _ in items]
    axis = max(range(3), key=lambda k: max(c[k] for c in cent) - min(c[k] for c in cent))
    order = sorted(range(len(items)), key=lambda i: cent[i][axis])
    items = [items[i] for i in order]
    mid = len(items) // 2
    return _Node(lo, hi, _build(items[:mid], leaf_size), _build(items[mid:], leaf_size))


class BVH:
    def __init__(self, shapes, leaf_size=4):
        bounded = [(s.bounds(), s) for s in shapes if s.bounds() is not None]
        self.unbounded = [s for s in shapes if s.bounds() is None]
        self.root = _build(bounded, leaf_size) if bounded else None
        self.count = len(shapes)

    def intersect(self, ray, t_min, t_max):
        best = None
        for s in self.unbounded:
            h = s.intersect(ray, t_min, t_max)
            if h is not None:
                best, t_max = h, h.t
        if self.root is None:
            return best
        o, d = ray.origin, ray.direction
        inv = [1 / c if c != 0 else INF for c in d]
        stack = [self.root]
        while stack:
            node = stack.pop()
            if not _box_hit(node.lo, node.hi, o, inv, t_min, t_max):
                continue
            if node.shapes is not None:
                for s in node.shapes:
                    h = s.intersect(ray, t_min, t_max)
                    if h is not None:
                        best, t_max = h, h.t
            else:
                stack.append(node.left)
                stack.append(node.right)
        return best

    def depth(self):
        def d(n):
            return 1 if n is None or n.shapes is not None else 1 + max(d(n.left), d(n.right))
        return d(self.root)


def build(shapes, leaf_size=4):
    return BVH(shapes, leaf_size)
