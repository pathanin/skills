"""Simulate the pyramid break and render it. Provided; do not edit.

    python3 make_movie.py            # out/sheet.png (8 frames), out/final.png, out/metrics.json
    python3 make_movie.py --quick    # tiny images, for smoke tests
"""
import json
import os
import sys
import time

from ballpit import scene, sim
from ballpit.camera import Camera
from ballpit.png import write_png
from ballpit.raster import render
from ballpit.sheet import contact_sheet

DT = 1 / 240
STEPS = 600          # 2.5 s
FRAMES = 8
EYE, TARGET, FOV = (1.9, 1.45, 2.5), (0.0, 0.25, 0.0), 42


def main(quick=False):
    fw, fh = (40, 30) if quick else (200, 150)
    big = (80, 60) if quick else (640, 480)
    os.makedirs("out", exist_ok=True)
    world = scene.pyramid(layers=4)
    small_cam = Camera(EYE, TARGET, FOV, fw, fh)
    big_cam = Camera(EYE, TARGET, FOV, *big)
    frame_at = {round(k * STEPS / (FRAMES - 1)) for k in range(FRAMES)}
    e0 = sim.energy(world)
    e_max, pen_max, frames = e0, 0.0, []
    t0 = time.time()
    for s in range(STEPS + 1):
        if s:
            sim.step(world, DT)
            e_max = max(e_max, sim.energy(world))
            pen_max = max(pen_max, sim.max_penetration(world))
        if s in frame_at:
            frames.append(render(world, small_cam))
    write_png("out/sheet.png", contact_sheet(frames, cols=4))
    write_png("out/final.png", render(world, big_cam))
    metrics = {
        "balls": len(world.balls),
        "energy_start": round(e0, 4),
        "energy_end": round(sim.energy(world), 4),
        "energy_max_ratio": round(e_max / e0, 4),
        "max_penetration": round(pen_max, 5),
        "finite": sim.finite(world),
        "seconds": round(time.time() - t0, 1),
    }
    with open("out/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
