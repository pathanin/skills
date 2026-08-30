#!/usr/bin/env python3
"""Measure a design reference instead of eyeballing it.

Subcommands:
  palette <image>            quantized palette with measured coverage percentages
                             (--role pins a small role the quantizer would merge away)
  margins <image>            content bounding box, as a percentage of the canvas
  squint <image> --out P     downscaled mass-distribution view for the squint test
  diff <reference> <rebuild> Step 5 reconstruct-and-diff verdict; exits non-zero on FAIL

Requires Pillow and numpy. Soft-detected: if either is missing the script says so
and exits non-zero, so a check that cannot run never reports success.
"""

import argparse
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError as e:
    sys.exit(f"missing dependency: {e.name}. Install with: pip install pillow numpy")

# Step 5 pass thresholds. All four must hold.
MAX_ROLE_DELTA_PTS = 3.0
MAX_TOTAL_DELTA_PTS = 8.0
MAX_SQUINT_MAE = 0.10
MAX_BLOCK_DELTA = 0.20

# Absolute point deltas are blind to small load-bearing roles: an accent going
# from 1% to 3% of the canvas is a different design, and only moves 2 points.
# 60/30/10 and 90/8/2 are two unrelated designs — this is the bar that says so.
MAX_RELATIVE_DELTA = 0.25
RELATIVE_MIN_COVERAGE_PCT = 0.3

SQUINT_GRID = 16
BLOCK_GRID = 8

# Buckets below this are anti-aliasing noise, not roles. Pin small real roles
# with --role instead of lowering it. A pinned role is never subject to this
# floor, nor to RELATIVE_MIN_COVERAGE_PCT — pinning IS the assertion it is real.
NOISE_FLOOR_PCT = 0.5


def load(path, max_side=1200):
    """Open as RGB, downscaled so quantization is fast and stable."""
    img = Image.open(path).convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return img


def quantize(img, n_colors):
    """Return [(hex, coverage_pct, (r,g,b))] sorted by coverage, descending."""
    q = img.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = q.getpalette()
    total = q.width * q.height
    out = []
    for count, idx in q.getcolors(total):
        r, g, b = pal[idx * 3 : idx * 3 + 3]
        out.append((f"#{r:02x}{g:02x}{b:02x}", 100.0 * count / total, (r, g, b)))
    return sorted(out, key=lambda c: -c[1])


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def coverage_by_basis(img, basis):
    """Assign every pixel to its nearest basis colour; return coverage % per basis entry.

    Comparing two independent quantizations is unsound — the palettes are ordered
    separately, so a noise bucket in one gets matched against a role in the other.
    A fixed basis measures both images on the same axes.
    """
    a = np.asarray(img).astype(np.int32).reshape(-1, 3)
    b = np.array(basis, dtype=np.int32)
    d = ((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)
    counts = np.bincount(d.argmin(axis=1), minlength=len(basis))
    return 100.0 * counts / len(a)


def build_basis(img, n_colors, roles):
    """Quantized buckets above the noise floor, plus every pinned role.

    Returns (basis, pinned) where pinned[i] is True for a colour supplied via
    --role. Pinned roles bypass the noise floor entirely: the quantizer merges a
    0.03% accent into whatever large bucket is nearest, and per doctrine that
    accent is exactly where fidelity dies.
    """
    basis, pinned = [], []

    def add(rgb, is_pinned):
        # Dedupe against quantized buckets only. A pinned role often re-adds a bucket
        # the quantizer already found, and there the exact spec hex wins. But two
        # PINNED roles never collapse into each other however close they sit: paper
        # #f5f5f7 and card #ffffff are 264 units apart and are two different roles
        # covering 53% and 29%. Pinning both is the assertion that both are real.
        for i, k in enumerate(basis):
            if sum((a - b) ** 2 for a, b in zip(rgb, k)) <= 24 ** 2:
                if pinned[i]:
                    if is_pinned:
                        break  # both asserted — keep them separate
                    return     # a quantized bucket next to a pinned role is that role
                if is_pinned:  # the exact spec hex beats the quantizer's guess
                    basis[i], pinned[i] = rgb, True
                return
        basis.append(rgb)
        pinned.append(is_pinned)

    for c in quantize(img, n_colors):
        if c[1] >= NOISE_FLOOR_PCT:
            add(c[2], False)
    for h in roles:
        add(hex_to_rgb(h), True)
    return basis, pinned


def cmd_palette(args):
    img = load(args.image)
    print(f"canvas: {img.width}x{img.height} (analysis raster)")

    if not args.role:
        colors = quantize(img, args.colors)
        print("hex        coverage%   rgb")
        for hexv, pct, rgb in colors:
            print(f"{hexv}   {pct:8.2f}   {rgb}")
        print(f"sum: {sum(c[1] for c in colors):.2f}%")
        print(
            "\nThis is the UNPINNED pass. The quantizer merges any role smaller than\n"
            "roughly 1% into its nearest large bucket, so a hex here may be a blend of\n"
            "two real roles and exist nowhere in the design. Read the small roles off\n"
            "the image (accent type, link colour, inverted grounds), then re-run:\n"
            "  measure.py palette <image> --role '#hex' --role '#hex' ...\n"
            "and write down THAT run's numbers, not these."
        )
        return

    basis, pinned = build_basis(img, args.colors, args.role)
    cov = coverage_by_basis(img, basis)
    print("hex        coverage%   rgb                 source")
    for rgb, pct, is_pinned in sorted(
        zip(basis, cov, pinned), key=lambda t: -t[1]
    ):
        hexv = "#%02x%02x%02x" % rgb
        print(f"{hexv}   {pct:8.3f}   {str(rgb):18s}  {'pinned' if is_pinned else 'quantized'}")
    print(f"sum: {sum(cov):.2f}%")
    print(
        "\nEvery pixel is assigned to its nearest basis colour, so these sum to 100.\n"
        "A pinned role still absorbs nearby pixels that are not that role — an orange\n"
        "photograph inflates an orange accent. If a role's number looks too big, pin a\n"
        "separate imagery role near it and re-run; the accent will drop to its true value."
    )
    print("\nName each of these descriptively ('dusty plum'), never as a token id.")


def cmd_margins(args):
    """Content bbox vs. canvas, treating the dominant colour as background."""
    img = load(args.image)
    a = np.asarray(img).astype(np.int16)
    bg = np.array(quantize(img, 8)[0][2], dtype=np.int16)
    # A pixel is content if it is perceptibly off the dominant colour.
    dist = np.abs(a - bg).sum(axis=2)
    content = dist > args.threshold
    h, w = content.shape
    rows = np.flatnonzero(content.mean(axis=1) > args.min_fill)
    cols = np.flatnonzero(content.mean(axis=0) > args.min_fill)
    if not len(rows) or not len(cols):
        sys.exit("no content detected — lower --min-fill or --threshold")
    top, bottom = rows[0], h - 1 - rows[-1]
    left, right = cols[0], w - 1 - cols[-1]
    print(f"background: #{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}")
    print("margins as % of canvas (use these, never pixels):")

    touching = False
    for name, px, span in (("top", top, h), ("right", right, w),
                           ("bottom", bottom, h), ("left", left, w)):
        if px == 0:
            touching = True
            print(f"  {name:6s}  bleed-or-crop — content reaches this edge, not a measurable margin")
        else:
            print(f"  {name:6s} {100.0 * px / span:6.2f}")

    if touching:
        print(
            "\nAn edge the content touches is EITHER a deliberate bleed (a row overflows\n"
            "the margin on purpose) OR a crop (the screenshot was cut there). This script\n"
            "cannot tell which, and 0 is not the answer to either. Resolve it from the\n"
            "image: a bleed is a design fact and usually the weird_move; a crop is an\n"
            "artefact of capture. Record the opposite edge's value as the margin rule and\n"
            "set the touched edge to unknown, or omit it. Never write 0."
        )


def grid_means(img, n):
    """Mean luminance per cell of an n x n grid, normalized 0-1."""
    g = img.convert("L").resize((n, n), Image.Resampling.BOX)
    return np.asarray(g).astype(np.float64) / 255.0


def cmd_squint(args):
    img = load(args.image)
    small = img.convert("L").resize((SQUINT_GRID, SQUINT_GRID), Image.Resampling.BOX)
    small.resize((512, 512), Image.Resampling.NEAREST).save(args.out)
    print(f"wrote {args.out}")
    print("Squint test: does the mass distribution match the reference at 3 metres?")


def cmd_diff(args):
    ref, reb = load(args.reference), load(args.rebuild)

    # One fixed basis from the reference: quantized buckets above the noise floor
    # plus every role pinned with --role. Small accents get quantized away
    # otherwise, and per doctrine the accent is exactly where fidelity dies.
    basis, pinned = build_basis(ref, args.colors, args.role)
    if not basis:
        sys.exit("no basis colours survived the noise floor — raise --colors")

    ref_cov = coverage_by_basis(ref, basis)
    reb_cov = coverage_by_basis(reb, basis)
    deltas = np.abs(ref_cov - reb_cov)

    print("coverage per reference role (both images measured on the same basis):")
    worst_rel, worst_rel_role = 0.0, "n/a"
    for rgb, rp, bp, d, is_pinned in zip(basis, ref_cov, reb_cov, deltas, pinned):
        hexv = "#%02x%02x%02x" % rgb
        tag = " pinned" if is_pinned else ""
        line = f"  {hexv}{tag}  ref {rp:6.3f}%   rebuild {bp:6.3f}%   delta {d:5.2f} pts"
        # A pinned role is exempt from the coverage floor. The floor exists to stop
        # anti-aliasing noise dominating the relative bar — but the roles that carry
        # a design's identity (a 0.03% accent, a 0.2% link) live below it, and
        # exempting them is exactly the failure the relative bar was written to catch.
        if is_pinned or rp >= RELATIVE_MIN_COVERAGE_PCT:
            if rp > 0:
                rel = d / rp
                line += f"   ({rel:+.0%} relative)"
                if rel > worst_rel:
                    worst_rel, worst_rel_role = rel, hexv
            else:
                line += "   (pinned role absent from reference — check the hex)"
        print(line)

    worst_role = max(deltas)
    total = sum(deltas)
    squint_mae = float(np.abs(grid_means(ref, SQUINT_GRID) - grid_means(reb, SQUINT_GRID)).mean())
    worst_block = float(np.abs(grid_means(ref, BLOCK_GRID) - grid_means(reb, BLOCK_GRID)).max())

    checks = [
        ("worst role coverage delta", worst_role, MAX_ROLE_DELTA_PTS, "pts"),
        ("total coverage delta", total, MAX_TOTAL_DELTA_PTS, "pts"),
        (f"worst relative role delta ({worst_rel_role})", worst_rel, MAX_RELATIVE_DELTA, ""),
        ("squint MAE (16x16)", squint_mae, MAX_SQUINT_MAE, ""),
        ("worst block delta (8x8)", worst_block, MAX_BLOCK_DELTA, ""),
    ]
    print()
    failed = False
    for name, value, bar, unit in checks:
        ok = value <= bar
        failed |= not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {value:.3f}{unit} (bar {bar}{unit})")

    print("\nAlso check by hand: display_to_body_ratio within +/-10%.")
    if failed:
        print("Every failing metric is a field dna.json forgot. Fold it in and run again.")
        print("Stop at 4 passes. Then still write both files, set")
        print("reconstruction.final_metrics.passed to false, and name the failing metric")
        print("and its margin in dna.md. Never relax a bar to turn it green.")
        sys.exit(1)
    print("Reconstruction passes. Record final_metrics in dna.json.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("palette")
    a.add_argument("image")
    a.add_argument("--colors", type=int, default=8)
    a.add_argument("--role", action="append", default=[], metavar="HEX",
                   help="pin a role the quantizer would merge away, e.g. --role '#b74400'. "
                        "Run once bare to see the buckets, then re-run pinning every small "
                        "role and record THAT run's coverage.")
    a.set_defaults(func=cmd_palette)

    b = sub.add_parser("margins")
    b.add_argument("image")
    b.add_argument("--threshold", type=int, default=30, help="RGB manhattan distance from background")
    b.add_argument("--min-fill", type=float, default=0.005, help="share of a row/col that must be content")
    b.set_defaults(func=cmd_margins)

    c = sub.add_parser("squint")
    c.add_argument("image")
    c.add_argument("--out", default="squint.png")
    c.set_defaults(func=cmd_squint)

    d = sub.add_parser("diff")
    d.add_argument("reference")
    d.add_argument("rebuild")
    d.add_argument("--colors", type=int, default=12)
    d.add_argument("--role", action="append", default=[], metavar="HEX",
                   help="pin a spec role into the basis, e.g. --role '#be3c28'. "
                        "Use for accents small enough to be quantized away.")
    d.set_defaults(func=cmd_diff)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
