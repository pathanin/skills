import math


def contact_sheet(frames, cols=4, gutter=2, bg=(16, 16, 16)):
    h, w = len(frames[0]), len(frames[0][0])
    nrows = math.ceil(len(frames) / cols)
    W = cols * w + (cols + 1) * gutter
    H = nrows * h + (nrows + 1) * gutter
    out = [[tuple(bg)] * W for _ in range(H)]
    for k, fr in enumerate(frames):
        x0 = gutter + (k % cols) * (w + gutter)
        y0 = gutter + (k // cols) * (h + gutter)
        for y in range(h):
            out[y0 + y][x0:x0 + w] = [tuple(p) for p in fr[y]]
    return out
