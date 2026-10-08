import math


def luminance(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def auto_exposure(pixels, key=0.18):
    """exposure = key / exp(mean(log(1e-4 + luminance))) over every pixel of a list of rows."""
    logs = [math.log(1e-4 + max(0.0, luminance(c))) for row in pixels for c in row]
    return key / math.exp(sum(logs) / len(logs))


def _srgb(x):
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def to_srgb8(color, exposure=1.0):
    """Exponential tone map (1 - exp(-c * exposure)), then the sRGB curve, then round to 0..255."""
    out = []
    for c in color:
        v = 1.0 - math.exp(-max(0.0, c) * exposure)
        out.append(max(0, min(255, round(_srgb(v) * 255))))
    return tuple(out)


def to_rows(pixels, exposure):
    return [[to_srgb8(c, exposure) for c in row] for row in pixels]
