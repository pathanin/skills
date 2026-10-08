# ballpit: modules to build

A pyramid of balls in a box is hit by a heavy cue ball. `make_movie.py` simulates 2.5 s and renders an 8-frame contact sheet (`out/sheet.png`), a large final frame (`out/final.png`) and `out/metrics.json`.

Provided, do not edit: `world.py` (the `Ball` / `World` contract), `vec.py`, `png.py`, `sim.py`, `make_movie.py`, `tests/`.

Seven modules are missing. Each is its own file under `ballpit/`, uses only the standard library plus `ballpit.world` and `ballpit.vec`, and has its own test file in `tests/`. Coordinates are metres, `y` is up, the floor is `y = 0`.

## `integrate.py`: `advance(world, dt)`

Semi-implicit Euler, in place, for every ball: first `vel[1] += world.gravity * dt`, then `pos += vel * dt` (all three axes, using the updated velocity).

## `walls.py`: `resolve(world)`

In place, for every ball and each of the six box planes (floor `y = 0`, ceiling `y = world.height`, `x = ±half_width`, `z = ±half_width`): if the ball penetrates the plane, move it back along that axis so it just touches (`pos = plane ∓ radius`). Then, only if its velocity on that axis points into the plane, set that velocity component to `-restitution * component`. Other components are untouched.

## `collide.py`: `resolve(world)`

One pass, in place, over all pairs `i < j` in list order. For a pair with centre distance `d < ri + rj` and `d > 0`:

1. `n = (pj - pi) / d`, `overlap = ri + rj - d`.
2. Push apart by inverse mass: `pi -= n * overlap * mj / (mi + mj)`, `pj += n * overlap * mi / (mi + mj)`.
3. `vrel = dot(vj - vi, n)`. Only if `vrel < 0`: `J = -(1 + restitution) * vrel / (1/mi + 1/mj)`, `vi -= n * J / mi`, `vj += n * J / mj`.

Pairs with `d == 0` are skipped.

## `camera.py`: `Camera(eye, target, fov_deg, width, height, up=(0, 1, 0))`

- `forward = normalize(target - eye)`, `right = normalize(cross(forward, up))`, `true_up = cross(right, forward)`. `fov_deg` is the vertical field of view. Let `t = tan(radians(fov_deg) / 2)` and `aspect = width / height`.
- `ray(px, py) -> (origin, direction)`: through the centre of pixel `(px, py)`, row `py = 0` at the top. `sx = (2 * (px + 0.5) / width - 1) * t * aspect`, `sy = (1 - 2 * (py + 0.5) / height) * t`, `direction = normalize(forward + right * sx + true_up * sy)`, `origin = eye`.
- `project(point) -> (x, y) | None`: the inverse, in float pixel coordinates (pixel centres at `+0.5`). `None` if the point is not in front of the camera (`dot(point - eye, forward) <= 0`).

## `raster.py`: `render(world, camera) -> rows`

Ray-trace one ray per pixel (`camera.ray`). Returns `camera.height` rows of `camera.width` `(r, g, b)` int tuples, each channel rounded and clamped to 0..255.

- **Hits:** the nearest sphere hit with `t > 1e-6`, or the floor plane `y = 0` within the box (`|x| <= half_width` and `|z| <= half_width`) when the ray points down. A sphere in front of the floor wins.
- **Light:** direction to the light `L = normalize((-0.4, 1.0, 0.3))`. Brightness `= 0.25 + 0.75 * max(0, dot(normal, L))`, where the diffuse part becomes 0 if the point is in shadow. A point is in shadow when a ray from `point + normal * 1e-4` towards `L` hits any sphere.
- **Sphere colour:** `ball.color * brightness`.
- **Floor colour:** a checkerboard of 0.25 m squares: `(200, 200, 200)` when `floor(x / 0.25) + floor(z / 0.25)` is even, else `(120, 120, 120)`, times brightness (floor normal `(0, 1, 0)`).
- **Background** (ray hits nothing): a vertical gradient from `(30, 34, 48)` on row 0 to `(70, 76, 96)` on the last row, linear in the row index.

## `scene.py`: `pyramid(layers=4) -> World`

- Ball radius `r = 0.12`, mass `1.0`, spacing `d = 2 * r * 1.001`.
- A tetrahedral stack: layer `k` (0 = bottom) is a triangle with `n = layers - k` balls per side. In each layer, row `i` (0..n-1) holds balls `j` (0..i) at `x = (j - i / 2) * d`, `z = i * d * sqrt(3) / 2`. Then shift the layer so its centroid is at `x = 0, z = 0`. Layer `k` sits at `y = r * 1.001 + k * d * sqrt(2 / 3)`.
- Colour by layer: bottom `(230, 80, 60)`, top `(250, 200, 60)`, linear in `k / (layers - 1)` per channel, rounded to ints.
- All pyramid balls start at rest. Order: layer by layer from the bottom, rows and balls in the order above.
- Then one cue ball, **last** in the list: `pos [-0.85, 0.3, 0.02]`, `vel [6.0, 0.6, 0.0]`, radius `0.12`, mass `2.0`, colour `(240, 240, 240)`.
- `World(balls, half_width=1.0, height=3.0, gravity=-9.81, restitution=0.9)`.

## `sheet.py`: `contact_sheet(frames, cols=4, gutter=2, bg=(16, 16, 16)) -> rows`

Lay equally sized frames (each a list of rows) left to right, top to bottom, `cols` per row, with `gutter` pixels of `bg` around and between them. Output width `cols * w + (cols + 1) * gutter`, height `nrows * h + (nrows + 1) * gutter` with `nrows = ceil(len(frames) / cols)`. Frame `k` has its top-left corner at `(gutter + (k % cols) * (w + gutter), gutter + (k // cols) * (h + gutter))`. Unused cells stay `bg`.
