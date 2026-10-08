"""Render scene.json. Provided; do not edit.

    python3 render.py            # out/final.png (400x300), out/views.png (4 orbit views), out/metrics.json
    python3 render.py --quick    # tiny images, for smoke tests
"""
import json
import os
import sys
import time

from rt import scene_io, tonemap, tracer
from rt.camera import Camera
from rt.png import write_png

HERE = os.path.dirname(os.path.abspath(__file__))


def render(scene, camera):
    return [[tracer.trace(camera.ray(px, py), scene) for px in range(camera.width)] for py in range(camera.height)]


def sheet(frames, gutter=2, bg=(16, 16, 16)):
    h, w = len(frames[0]), len(frames[0][0])
    out = [[bg] * (len(frames) * w + (len(frames) + 1) * gutter) for _ in range(h + 2 * gutter)]
    for k, fr in enumerate(frames):
        x0 = gutter + k * (w + gutter)
        for y in range(h):
            out[gutter + y][x0:x0 + w] = fr[y]
    return out


def main(quick=False):
    w, h = (48, 36) if quick else (400, 300)
    vw, vh = (24, 18) if quick else (160, 120)
    os.makedirs("out", exist_ok=True)
    t0 = time.time()
    scene = scene_io.load(os.path.join(HERE, "scene.json"), w, h)
    pixels = render(scene, scene.camera)
    exposure = tonemap.auto_exposure(pixels)
    write_png("out/final.png", tonemap.to_rows(pixels, exposure))
    views = []
    for angle in (35, 125, 215, 305):
        cam = Camera.orbit([0.0, 0.6, 0.0], 6.0, 2.6, angle, 40, vw, vh)
        views.append(tonemap.to_rows(render(scene, cam), exposure))
    write_png("out/views.png", sheet(views))
    metrics = {"primitives": scene.meta.get("primitives"), "exposure": round(exposure, 4),
               "mean_luminance": round(sum(tonemap.luminance(c) for r in pixels for c in r) / (w * h), 5),
               "seconds": round(time.time() - t0, 1)}
    with open("out/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
