# tinyrt: modules to build

`tinyrt` is a Whitted-style ray tracer: `python3 render.py` loads `scene.json`, traces one ray per pixel, tone-maps, and writes `out/final.png` (400×300), `out/views.png` (four orbit views) and `out/metrics.json`.

Provided, do not edit: `rt/types.py` (the data contract: `Ray`, `Material`, `Hit`, `PointLight`, `DirectionalLight`, `Scene`, plus the shape and texture protocols in its docstring), `rt/vec.py`, `rt/png.py`, `render.py`, `scene.json`, `assets/`, `tests/`.

Thirteen modules are missing. `mesh.py` and `obj.py` build `Triangle`s and `tracer.py` calls `lighting`; their tests substitute a stub when the real module isn't there yet, so each module can be built and tested on its own. Each is its own file, uses only the standard library and `rt.types` / `rt.vec` (plus the modules named in its section), and has its own test file in `tests/`. Conventions everywhere:
- Colours are linear RGB float tuples; `y` is up.
- A `Hit.normal` is unit length and always faces against the ray. `front_face` is `True` when the ray hits the outside, judged against the shape's outward (geometric) normal.
- Every `intersect(ray, t_min, t_max)` returns the nearest hit with `t_min < t < t_max`, or `None`.

## 1. `rt/shapes/sphere.py`: `Sphere(center, radius, material)`

- Ray-sphere quadratic with `b = dot(o - c, d)`, `c' = |o - c|² - r²`. Take the smaller root if it's in range, else the larger.
- Outward normal `(p - center) / radius`.
- `uv`: `u = (atan2(-n.z, n.x) + π) / (2π)`, `v = acos(-n.y) / π`, computed from the outward normal, with the `acos` argument clamped to [-1, 1].
- `bounds()`: `center ± radius`.

## 2. `rt/shapes/plane.py`: `Plane(point, normal, material)` and `Disk(center, normal, radius, material)`

- Store the normal normalized. Tangents: `a = (1, 0, 0)` if `|n.x| < 0.9`, else `(0, 1, 0)`; `tu = normalize(cross(n, a))`; `tv = cross(n, tu)`.
- Hit: `denom = dot(n, d)`; there's no hit if `|denom| < 1e-9`; otherwise `t = dot(point - o, n) / denom`.
- `Plane` uv: `(dot(p - point, tu), dot(p - point, tv))`. `Plane.bounds()` is `None`.
- `Disk`: a hit counts only within `radius` of `center`. uv: `(0.5 + dot(rel, tu) / (2r), 0.5 + dot(rel, tv) / (2r))`.
- `Disk.bounds()`: `center ± r * sqrt(1 - n_k²)` per axis `k`.

## 3. `rt/shapes/box.py`: `Box(lo, hi, material)`

- Axis-aligned. Sort the corners per axis so `lo <= hi`.
- Slab test: on an axis where `|d_k| < 1e-12`, miss if `o_k` is outside `[lo_k, hi_k]`, else ignore that axis. Track the entering `t` and axis, and the exiting `t` and axis.
- Use the entering hit if it's in range, else the exiting hit (`front_face = False`).
- Normal: ±1 on the hit axis; the outward sign is `-1` on the `lo` face and `+1` on the `hi` face, flipped for an inside hit.
- uv: the other two axes `a < b`, `u = (p_a - lo_a) / (hi_a - lo_a)`, `v` likewise for `b`.

## 4. `rt/shapes/triangle.py`: `Triangle(a, b, c, material, normals=None)`

- Möller–Trumbore with `e1 = b - a`, `e2 = c - a`; no hit when `|det| < 1e-9`. Barycentrics `u`, `v` must satisfy `u ≥ 0`, `v ≥ 0`, `u + v ≤ 1`.
- `geo_normal = normalize(cross(e1, e2))`; `front_face = dot(d, geo_normal) < 0`.
- Shading normal: `normalize(na·(1-u-v) + nb·u + nc·v)` when `normals` (three vectors, normalized on construction) is given, else `geo_normal`. Flip it for a back-face hit. `uv = (u, v)`.
- Expose `geo_normal`, `a`, `b`, `c` as attributes. `bounds()`: the min/max of the three vertices.

## 5. `rt/mesh.py`: procedural meshes, returning lists of `Triangle`

Every triangle's `geo_normal` must point outward (counter-clockwise winding seen from outside).
- `icosphere(center, radius, subdivisions, material)`: start from the 12-vertex icosahedron (vertices `(±1, ±φ, 0)`, `(0, ±1, ±φ)`, `(±φ, 0, ±1)`, normalized; 20 faces). Each subdivision splits every triangle into 4 at its edge midpoints, pushed out to the unit sphere, with shared midpoints de-duplicated. Vertex normals are the unit directions; positions are `center + dir · radius`. Gives `20 · 4^s` triangles.
- `torus(center, major, minor, segments, rings, material)`: around the y axis. Point `(i, j)`: `θ = 2πi/segments`, `φ = 2πj/rings`, `n = (cos φ cos θ, sin φ, cos φ sin θ)`, `p = center + ((R + r cos φ) cos θ, r sin φ, (R + r cos φ) sin θ)`. Each grid cell becomes 2 triangles with those vertex normals: `segments · rings · 2` triangles.
- `cylinder(base, radius, height, segments, material, caps=True)`: upright from `base` (the bottom cap centre). For each segment, 2 side triangles with smooth normals `(cos a, 0, sin a)`, and with `caps` a top and a bottom cap triangle (flat normals). That's `4 · segments` triangles with caps, `2 · segments` without.

## 6. `rt/obj.py`: `parse(text, material, scale=1.0, offset=(0, 0, 0))`, `load(path, material, scale, offset)`

Wavefront OBJ to a list of `Triangle`.
- `v x y z` becomes `[x·scale + offset_x, …]`. `vn x y z` is a normal.
- `f` corners can be `v`, `v/vt`, `v//vn` or `v/vt/vn`. Indices are 1-based; a negative index counts back from the end of the list so far.
- A polygon with n corners is fan-triangulated from its first corner. Normals are used only when all three corners of a triangle have one.
- `#` starts a comment; any other tag is ignored. A face with fewer than 3 corners, or an out-of-range index, raises `ValueError` naming the line number.

## 7. `rt/bvh.py`: `build(shapes, leaf_size=4) -> BVH`

- Shapes whose `bounds()` is `None` go in a separate list, tested linearly. The rest form a tree.
- Node boxes are the union of child bounds. Split on the axis where the centroids spread widest, sorting by centroid on that axis and cutting at `len // 2`. A leaf holds `≤ leaf_size` shapes.
- `BVH.intersect(ray, t_min, t_max)` returns the nearest hit over all shapes, the same answer a brute-force loop gives. Shrink `t_max` as hits are found, and skip a node whose box the ray misses within `[t_min, t_max]`.
- Also expose `BVH.depth()` (a leaf-only tree has depth 1).

## 8. `rt/camera.py`: `Camera(eye, target, up, vfov, width, height)`

- `forward = normalize(target - eye)`, `right = normalize(cross(forward, up))`, `true_up = cross(right, forward)`. Let `half_h = tan(radians(vfov) / 2)` and `half_w = half_h · width / height`.
- `ray(px, py, sx=0.5, sy=0.5)`: the ray through image point `(px + sx, py + sy)`, row 0 at the top. With `x = (2(px + sx)/width - 1) · half_w` and `y = (1 - 2(py + sy)/height) · half_h`, the direction is `normalize(forward + right·x + true_up·y)` and the origin is `eye`.
- Classmethod `orbit(target, distance, height, angle_deg, vfov, width, height_px)`: `eye = target + (distance · sin a, height, distance · cos a)`, looking at `target` with up `(0, 1, 0)`.

## 9. `rt/textures.py`: `Solid`, `Checker`, `Stripes`, `Noise`, `Marble`, plus `value_noise` and `fbm`

Each texture has `sample(uv, point) -> (r, g, b)`.
- `Solid(color)` always returns `color`.
- `Checker(scale, a, b)`: `a` when `Σ floor(p_k / scale + 1e-4)` over x, y, z is even, else `b`.
- `Stripes(count, a, b)`: `a` when `floor(u · count)` is even, else `b`.
- `value_noise(p, seed=0)`: the lattice hash is `h = sin(i·127.1 + j·311.7 + k·74.7 + seed·19.19) · 43758.5453`, taking `h - floor(h)`. Interpolate trilinearly between the 8 corners with `smooth(t) = t²(3 - 2t)` on the fractional parts (x first, then y, then z).
- `fbm(p, octaves=4, seed=0)`: `Σ value_noise(p·2^o)/2^o` over `o` in `0..octaves-1`, divided by `Σ 1/2^o`.
- `Noise(scale, a, b, seed=0)`: `lerp(a, b, fbm(point · scale, 4, seed))`.
- `Marble(scale, a, b, turbulence=1.0, seed=0)`: with `q = point · scale`, `t = 0.5 + 0.5 sin(q.x + turbulence · 6.2832 · fbm(q, 4, seed))`, giving `lerp(a, b, t)`.

## 10. `rt/lighting.py`: `surface_color(hit)`, `shade(hit, view_dir, lights, ambient, occluded)`

- `surface_color`: `texture.sample(hit.uv, hit.point)` when the material has a texture, else `material.color`.
- `shade` starts from `ambient · base`, per channel. For each light:
  - **Point light:** `L = normalize(position - p)`, `dist = |position - p|`, `radiance = color · intensity / dist²`.
  - **Directional light:** `L = normalize(direction)`, `dist = inf`, `radiance = color · intensity`.
- Skip the light if `dot(n, L) ≤ 0` or `occluded(p + n·1e-4, L, dist)` is true.
- Otherwise add `radiance · (diffuse · base · dot(n, L) + specular · max(0, dot(n, H))^shininess)`, with `H = normalize(L + view_dir)`. `view_dir` points from the surface to the viewer.
- Return the colour tuple, unclamped.

## 11. `rt/tracer.py`: `trace(ray, scene, depth=0)`, `background(scene, direction)`, `schlick(cos_i, ior)`

Import lighting as `from rt import lighting` and call `lighting.shade(...)` through the module, so tests can substitute it.

- `hit = scene.bvh.intersect(ray, 1e-4, inf)`. On a miss, return `background`: `lerp(scene.background_bottom, scene.background_top, 0.5 · (d.y + 1))`.
- `occluded(o, dir, max_t)`: any `scene.bvh` hit in `(1e-4, max_t - 1e-4)`, or `(1e-4, inf)` when `max_t` is infinite.
- `local = lighting.shade(hit, -d, scene.lights, scene.ambient, occluded)`, and `color = local · (1 - reflect - transparency)`. At `depth >= scene.max_depth`, return `color`.
- If `reflect > 0`, add `reflect · trace(Ray(p + n·1e-4, reflect(d, n)), depth + 1)`.
- If `transparency > 0`:
  - Set `eta = 1/ior` on a front-face hit, else `ior`. Let `cos_i = min(1, -dot(d, n))` and `sin²t = eta²(1 - cos_i²)`.
  - Trace the reflected ray `R` as above.
  - On total internal reflection (`sin²t > 1`), add `transparency · R`.
  - Otherwise the refracted direction is `eta·d + (eta·cos_i - sqrt(1 - sin²t))·n`, traced from `p - n·1e-4`. Add `transparency · ((1 - F)·refracted + F·R)` with `F = schlick(cos_i, ior)`, where `schlick = r0 + (1 - r0)(1 - cos_i)⁵` and `r0 = ((1 - ior)/(1 + ior))²`.
- Return a tuple.

## 12. `rt/scene_io.py`: `load(path, width, height, factories=None)`, `build(data, width, height, base_dir=".", factories=None)`, `default_factories()`

`build` turns the JSON object (the format of `scene.json`) into a `Scene`. `load` reads the file and passes its directory as `base_dir`. `default_factories()` imports the other modules inside the function (not at module top), so `scene_io` imports cleanly on its own. All construction goes through `factories`, a dict that defaults to `default_factories()`. Tests pass fakes, so call factories exactly as follows:

- `"camera"`: `(cam_json, width, height)`.
- `"bvh"`: `(objects)`.
- Each object type: `(obj_json, material, base_dir)`, returning a shape or a list of shapes, which get flattened into `objects`. Object types: `sphere`, `plane`, `disk`, `box`, `triangle`, `icosphere`, `torus`, `cylinder`, `obj`.
- Each texture type: `(tex_json)`. Texture types: `solid`, `checker`, `stripes`, `noise`, `marble`.
- The default factories map JSON keys to the constructors above:
  - `sphere`: `center`, `radius`. `plane`: `point`, `normal`. `disk`: `center`, `normal`, `radius`. `box`: `min`, `max`. `triangle`: `a`, `b`, `c`.
  - `icosphere`: `center`, `radius`, `subdivisions` (default 2). `torus`: `center`, `major`, `minor`, `segments` (default 32), `rings` (default 16). `cylinder`: `base`, `radius`, `height`, `segments` (default 24), `caps` (default true). `obj`: `path` relative to `base_dir`, `scale` (default 1), `offset` (default `[0, 0, 0]`).
  - Camera: `eye`, `target`, `up` (default `[0, 1, 0]`), `vfov` (default 40).
  - Textures: `checker`: `scale`, `a`, `b`. `stripes`: `count`, `a`, `b`. `noise`: `scale`, `a`, `b`, `seed` (default 0). `marble`: `scale`, `a`, `b`, `turbulence` (default 1), `seed` (default 0). `solid`: `color`.

Rules:
- **Materials:** each is a dict of `Material` fields plus an optional `texture` (`{"type": ..., ...}`) and an optional `extends` naming another material. Its fields are the parent's fields (resolved recursively) overridden by its own. An unknown field, an unknown parent or an `extends` cycle raises `ValueError`.
- **Missing material:** an object without `"material"` uses `"default"`, which is `Material()` unless the file defines it. An unknown material name raises `ValueError`.
- **Lights:** `{"type": "point", "position", "color" (default white), "intensity" (default 1)}` or `{"type": "directional", "direction", ...}`. Any other type raises `ValueError`.
- **Unknown types:** an unknown object type raises `ValueError` naming the object's index and type.
- **Scene fields:** `ambient` (default `(0.05, 0.05, 0.05)`); `background` `{top, bottom}` sets those `Scene` fields; `max_depth` sets `scene.max_depth`. `scene.meta = {"objects": <number of JSON objects>, "primitives": <len(objects)>}`.

## 13. `rt/tonemap.py`: `luminance`, `auto_exposure`, `to_srgb8`, `to_rows`

- `luminance(c) = 0.2126 r + 0.7152 g + 0.0722 b`.
- `auto_exposure(pixels, key=0.18)`: `key / exp(mean(log(1e-4 + max(0, luminance))))` over every pixel of a list of rows.
- `to_srgb8(color, exposure=1.0)`: per channel, `v = 1 - exp(-max(0, c) · exposure)`, then the sRGB curve (`12.92 v` if `v ≤ 0.0031308`, else `1.055 v^(1/2.4) - 0.055`), then round to int and clamp to 0..255. Returns a tuple.
- `to_rows(pixels, exposure)`: `to_srgb8` over a list of rows.
