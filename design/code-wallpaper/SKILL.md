---
name: code-wallpaper
description: Manual-only code-drawn wallpaper render, invoked with /code-wallpaper. Paints a landscape entirely in code, as oil on linen (multi-bristle stroke engine) or as layered paper cut (shadowed, hand-cut paper pieces), from one polygon scene in headless Chromium, and exports a PNG at any resolution — 4K, ultrawide, or phone.
argument-hint: "[scene, style (oil | paper cut), resolution, number of variations]"
disable-model-invocation: true
---

# Code wallpaper

Draw a landscape entirely in code and export it as a PNG at the size the user asks for, in one of two styles:

- **Oil** (default): a stroke engine paints over the scene with thousands of directional, multi-bristle brush strokes on a woven linen ground.
- **Paper cut**: every region becomes a sheet of cut paper with a rough edge and a soft drop shadow, stacked back to front.

Both styles use the same scene, a list of flat-coloured polygons, rendered in headless Chromium through Playwright.

## Inputs to settle first

- **Style**: `oil` unless the user asks for paper cut (or cut paper, papercraft, layered paper). Do not ask about style.
- **Scene**: the subject, time of day, mood and any must-have elements. If the user gives only a theme ("a beach"), pick the palette and composition yourself. If the user gives a reference photo, see **Reference photos** below.
- **Resolution**: default 3840 x 2160 (4K UHD). Common alternatives: 2560 x 1440, 5120 x 2160 (ultrawide), 1170 x 2532 or 1080 x 1920 (phone), 6016 x 3384 (6K). Stay at or below about 8000 px per side, because Chromium's canvas limit is roughly 16384 px per side and 268M px in total.
- **How many variations**: default 1. Make each variation a new scene (palette, time of day, focal side, horizon height), not only a new seed: a new `tseed` changes only the cut edges or brushwork, which is barely visible at wallpaper size.

Take these from the text after `/code-wallpaper`. Ask only when the scene is missing. Otherwise use the defaults for anything left out and state them in your first message.

## Coordinate system

- The logical canvas height is always H = 400. The logical width is W = round(400 x width / height), so W is 711 for 16:9, 948 for 21:9 and 225 for 9:16.
- **Compose the scene for the actual W.** A scene built for 711 does not reflow into portrait. For a new aspect ratio, place every element again (horizon, focal point, trees) relative to W.
- Stroke sizes are in logical units, so the texture looks the same at every resolution. Stroke counts scale with the area W x H.
- The image depends only on the scene, `seed`, `tseed` and W, not on the pixel size. Any resolution with the same W paints the same image, so a small render is an exact preview of the final one.

## Seeds

- `seed` drives `build`: every `C.rnd` call in the scene, so star positions, cloud outlines and scattered details. A new `seed` gives a new layout.
- `tseed` drives the texture: cut edges, brush strokes and grain. A new `tseed` keeps the layout and changes only the texture. It defaults to a value derived from `seed`.
- Set them per scene (`{seed:1101, tseed:7}`) or per render (`[seed]` argument, `--tseed=N`).

## Project layout and setup

Work in this layout inside the working folder:

```
src/      engine.html, render.js, helpers.js (copied from the skill), scene.js (you write it), node_modules/ (if installed)
output/   finished wallpapers only
```

1. Copy the assets from this skill's base directory. That is `${CLAUDE_PLUGIN_ROOT}`; if the variable is empty, use the "Base directory for this skill" path shown when the skill loads.
   ```bash
   mkdir -p src output && cp "${CLAUDE_PLUGIN_ROOT}"/assets/{engine.html,render.js,helpers.js} src/
   ```
   If `src/` already exists from an earlier run, copy the three files again (never overwrite `scene.js`), then delete any helper definitions that an older `scene.js` declares itself (see **Helpers**).
2. Use `engine.html`, `render.js` and `helpers.js` as they are. The one allowed edit is raising the oil stroke counts when the polishing loop says so.
3. Run renders from the working folder: `NODE_PATH=$(npm root -g) node src/render.js 0 3840 2160 output/<name>.png`.
   - `Cannot find module 'playwright'`: run `(cd src && npm i playwright)` and retry without `NODE_PATH`.
   - `render.js` launches Playwright's bundled Chromium and falls back to the installed Google Chrome by itself. Run `npx playwright install chromium` only when both fail, and not when `PLAYWRIGHT_BROWSERS_PATH` is set (browsers are preinstalled there, as in Claude Code on the web, so the error is something else).
4. Write previews and crops outside `output/`, in your scratchpad or temp directory, so `output/` only ever holds finished files.

## render.js

```
node src/render.js <scene_index> <width> <height> <out.png|out.jpg> [seed] [crop] [--tseed=N] [--crop-out=path]
```

- `seed`: overrides the scene's seed. Pass `''` to keep it.
- `crop` `x,y,w,h` (logical units): also writes that area at full resolution, to `--crop-out` or else to the system temp directory. It prints the crop's path. Read the crop, never the full-size file, which is tens of MB.
- `--tseed=N`: overrides the texture seed. `--seed=` and `--crop=` work as flags too.
- A `.jpg` output name writes JPEG at quality 92.
- It exits non-zero and prints `PAGE ERROR:` when the scene throws.

## What the engine does

**Oil** (the default) paints in these passes:

1. A linen ground with a woven grid.
2. A broad underpainting pass.
3. A mid pass.
4. A fine detail pass.
5. Edge strokes placed on region borders.
6. Extra strokes inside small regions such as windows and stars.
7. A multiply grain layer at full resolution.

The per-bristle lines, the highlight bristle and the shadow bristle are what make the strokes read as oil paint.

**Paper cut** (`style:'papercut'`) lays each region down as one sheet of cut paper, back to front. The first region fills the whole canvas. Every later piece gets:

1. A hand-cut edge: a jittered point every 3 units. The jitter is ±0.5 units, scaled down for thin pieces (strips, dots) so they keep their width. Set `jit` on a region to override it. Edges lying on the canvas frame run off the page instead, so no cut edge shows there.
2. A soft drop shadow down and to the right, cast onto everything beneath it.
3. A fill: `col` lightened 7% like pale construction paper, `grad` as a smooth vertical gradient, or `cf` baked into a smooth texture.
4. A paper-grain texture and a faint white rim along the cut.

Depth comes entirely from the stacking: each piece shadows the ones beneath it.

## scene.js (write per request)

`src/scene.js` defines `const SCENES=[...]`. Each entry is `{name, seed, tseed?, style?, ground?, build(C)}`, and `build` returns the regions **back to front** (later regions are painted on top).

- `style` is `'oil'` (the default) or `'papercut'`.
- To render one scene in both styles, add a copy after the array, for example `SCENES.push({...SCENES[0], name:'…-papercut', style:'papercut'})`. Add further scenes the same way. Don't write the copy inside the `SCENES=[...]` literal, because `SCENES` is not defined yet there.
- `ground` is the colour under everything: linen brown for oil, and dark board (`#2a2530`) for paper cut.
- `C` provides `{W,H,rnd,hex,mixc,gradAt,lerp,clamp}`. Always use `C.rnd`, never `Math.random`, so a seed reproduces the same image exactly.

Each region is `{pts:[[x,y],...], dir, jit?, ...colour}`:

- **Colour** is one of three options:
  - `col:'#hex'` or `col:[r,g,b]` for a flat colour. The array form takes `C.mixc` output directly.
  - `grad:[[y,'#hex'],...]` for a vertical gradient, used for skies, sea and ground.
  - `cf:(x,y)=>[r,g,b]` for any colour function, used for glows, light beams and shaded cliffs.
- **Stroke direction (`dir`)**, used by oil only (paper cut ignores it):
  - `sky`: wavy sky flow.
  - `horiz`: water, clouds and walls.
  - `hill`: gentle rolling curves.
  - `mtn`: diagonal mountain strokes.
  - `vert`: trunks, towers and cacti.
  - `angle` + `a`: a fixed angle in radians.
  - `radial` + `cx,cy`: strokes circle a point, used for sun, moon and halos.
  - `ray` + `cx,cy`: strokes point outward, used for beams and perspective roads.
  - `roof` + `rx`: the two slopes of a roof.
  - `pine` + `tx`: drooping pine branches.
  - `swirl` + `cx,cy`: foliage.
- **`jit`** (paper cut only): the cut-edge jitter in units, overriding the automatic value.
- **The first region must cover the entire canvas**, usually the sky. It is the fallback for every pixel.

### Helpers

`helpers.js` is loaded before `scene.js` and defines these globals. Use them directly. **Never redeclare them in `scene.js`**: a second `const TAU` (or any name below) throws `Identifier 'TAU' has already been declared`.

- `TAU`
- `circ(cx,cy,r,n=60,sx=1)`: disc or ellipse.
- `rect(x0,y0,x1,y1)`.
- `bandF(W,fn,y1,step=4)`: full-width band with top edge `y=fn(x)` and bottom `y1`.
- `blob(cx,cy,R,ph,sx,sy)`: lumpy rounded shape.
- `glowCF(C,sky,cx,cy,r,col,s)`: oil-only soft halo colour function.
- `pine(out,x,base,h,w,cols,snow)` and `roundTree(out,C,x,base,r,cols)`: push trees onto `out`.
- `lens(cx,cy,w,h)`: pointed horizontal sliver for glints, reflection rows and wave caps.
- `strip([[x,y,width],...])`: ribbon along a polyline, for cables, rivers and rigging.
- `cloud(cx,cy,w,h,ph=0)`: flat-bottomed cloud rising `h` above `cy`.
- `hump(x,c,w)`: smooth bump (1 at `c`) for building terrain profiles.
- `star4(x,y,r)`: four-point sparkle star.
- `persp(x0,x1,Z)`: for receding structures (bridges, roads, fences, piers).
  - `t=0` is at screen `x0` at full size; `t=1` is at `x1`, where the depth is `Z` times greater.
  - It returns `{x(t), t(X), s(X), z(t)}`. `x(t)` places evenly spaced world points on screen, `t(X)` inverts it, and `s(X)` is the size scale at screen `X`.
  - Space posts, hangers or truss panels evenly in `t`. Scale their widths by `s`.

Here is an example scene entry, a lighthouse cove at sunset for W = 711:

```js
const SCENES=[{ name:'lighthouse-sunset', seed:1101, build(C){ const {W,H}=C, o=[];
  const sky=[[0,'#3b3f7e'],[90,'#7b5c9a'],[170,'#d9728a'],[230,'#f8b56a']];
  o.push({pts:rect(0,0,W,H),grad:sky,dir:'sky'});
  o.push({pts:circ(190,228,120),cf:glowCF(C,sky,190,228,120,'#ffd9a0',.6),dir:'radial',cx:190,cy:228});
  o.push({pts:circ(190,222,30),col:'#ffcf72',dir:'radial',cx:190,cy:222});
  o.push({pts:rect(0,228,W,H),grad:[[228,'#5a5d9a'],[300,'#35507e'],[400,'#1f3558']],dir:'horiz'});
  for(let i=0;i<9;i++){ const y=236+i*i*2.2, hw=26-i*1.8; o.push({pts:rect(190-hw,y,190+hw,y+2+i*.35),col:i<3?'#ffd58a':'#f2a86a',dir:'horiz'}); }
  o.push({pts:[[W+2,H+2],[430,H+2],[452,300],[486,226],[520,160],[620,140],[W+2,128]],cf:(x,y)=>C.mixc(C.hex('#8a5a52'),C.hex('#3e2b35'),C.clamp((y-150)/250)),dir:'angle',a:1.25});
  // ...grass cap, lighthouse (tapered tower + stripe bands + lamp + roof), rocks, foam lines
  return o; } }];
```

## Composition guidance

- Give each wallpaper a clear focal point placed off-centre (roughly on the thirds), with one light source such as a sun, moon or lit windows.
- Across a set, vary the horizon height (low horizon with a big sky, or high horizon with lots of land), the focal side, and the palette (warm dusk, cold night, bright day).
- Use leading lines: a road, a river, a sun reflection, or a path into the scene.
- Build depth with layers: hazy far range, mid hills, detailed foreground. Make the near layers darker or more saturated.
- Keep important detail away from the centre-bottom if the image is a desktop wallpaper (icons and the dock sit there), and away from the top of a phone wallpaper (the clock sits there).
- Small details such as stars, birds, windows and glints need their own small regions so the small-region pass paints them crisply.
- Every small shape must read as something. At wallpaper size, small slivers scattered on water read as floating debris, and a tiny mast or antenna reads as a cross. Enlarge them until they read, or drop them.

For paper cut, also:

- Paper has no brushwork to carry detail, so every detail is its own piece stacked on top, such as snow caps, windows, doors and each tier of a pine.
- Keep to a limited palette of about 8 to 12 flat colours and simple, bold silhouettes.
- Pieces are separated only by their shadows, so give every depth band (far range, mid hills, near hills, water) a clear step in value from the band behind it.
- Replace `glowCF` halos with 2 or 3 flat concentric discs in progressively lighter tints around the sun or moon. A gradient halo cut from paper shows as a ghostly ring.
- Use `grad` for the sky and large water only. Use `cf` only for large pieces with a real edge, such as a shaded cliff.
- Draw a sun or moon reflection as rows of `lens` slivers across the path, broken by small gaps, brightest at the centre, with the path widening toward the viewer.
  - Keep each sliver clear of its neighbours, and drop any too short to read (under about 4 units).
  - A solid wedge reads as a ramp, and scattered single glints read as blobs.
- Water reads well as stacked wave bands (`bandF` with a sine top edge) that get taller, wider-spaced and darker toward the viewer. Draw each band's reflection rows right after the band, so the next band overlaps them.
- Thin structures (cables, hangers, masts, rigging) hold their width down to about 1.5 units, because the cut jitter scales down on thin pieces. Build them with `strip` or `rect`, and check them in a 1:1 crop (step 4).

### Reference photos

When the user supplies a photo, take from it these things and nothing else:
- the focal element and its position
- the horizon height
- the key silhouettes and landmark proportions
- the light direction
- a palette of 8 to 12 colours

Recompose for W instead of stretching: a 4:3 photo becomes a 16:9 wallpaper by widening the scene around the focal element, not by scaling it. Keep landmarks recognisable by their silhouettes, for example a bridge's tower shape, cable sag and deck angle. Leave out anything that won't read at paper-cut or brush scale.

## Workflow, including the polishing loop

1. Settle the style, the scene, the resolution and the number of variations, then compute W. Set up `src/` and `output/` (see **Project layout and setup**).
2. Write `src/scene.js`, one entry per wallpaper.
3. Render a preview of each wallpaper at (s x W) by (s x 400) px, with s = 2 for landscape and s = 3 for portrait (for example 1422 x 800 for W = 711), into your scratchpad or temp directory. This keeps the same W, so the preview shows exactly the image the final render will produce. A paper-cut render takes under a second up to 4K and about 2 seconds at 8K. An oil render takes about 6 seconds up to 4K.
4. **Review each preview visually** with the Read tool. Fix what you see, re-render only the changed scenes, and review again. Repeat until clean.
   - When the scene has pieces under about 3 units wide, render a 1:1 crop during this loop, not only at the end. Thin pieces look fine in the preview even when their cut edges pinch at full size. For example, `node src/render.js 0 3840 2160 <scratch>/full.png '' 150,170,240,135`, then Read the crop path it prints.
   - These are the problems found in earlier runs:
     - **(Oil) Linen showing through as brown flecks**: coverage is too thin. Raise the underpainting count (2400 x A) and the mid count (5200 x A). Do not lower them.
     - **Glow halos around small objects** (for example, glows behind houses looked like snowballs): drop the glow or make it much weaker. Only large light sources should get `glowCF` halos.
     - **Stripes that look like stairs**: evenly spaced, full-width ledges or strata look artificial. Use 3 or 4 short strata at irregular spacing, in a colour close to the base.
     - **Unreadable blobs**, such as a dark polygon on a cliff face, debris-like slivers on water, or a tiny mast that reads as a cross: remove them or make their meaning clear.
     - **Broken or disconnected shapes**, such as a road drawn in pieces: the polygon is self-intersecting. Order the points as the left edge up, then the right edge down.
     - **Focal element hidden**, such as a sun behind a mesa: check the draw order and the overlap, and move the element into a gap.
     - **(Oil) Elements lost in the texture**, such as hay bales: add a darker shadow region offset beneath them for contrast.
     - **(Oil) Regions too thin to paint**: anything under about 1.5 logical units wide gets overpainted. Widen it or add it later in the list.
     - **(Paper cut) Ghostly ring around the sun**: a `glowCF` halo. Replace it with flat concentric discs.
     - **(Paper cut) Bands that merge**: two neighbouring pieces too close in value. Lighten the farther one or darken the nearer one.
     - **(Paper cut) Specks instead of details**: pieces under about 2.5 units in both directions (dots, tiny shapes) are swallowed by their own shadow and rim. Enlarge them or drop them. Long thin strips are fine down to about 1.5 units wide.
     - **(Paper cut) Reflection reads as a ramp or as blobs**: redo it as rows of slivers (see the paper-cut guidance).
     - **(Paper cut) Pinched or zigzag strips at 1:1**: widen them toward 2 units, or set a smaller `jit` on those regions.
     - **JS errors**: `render.js` prints PAGE ERROR. Common causes:
       - a duplicate `const` inside `scene.js`, including redeclaring a helper from `helpers.js`
       - a region with no `col`, `grad` or `cf`
       - `-x**2`, which must be written `-(x**2)`
       - `region N has a non-finite point`: a `NaN` in `pts`, usually a negative number raised to a fractional power, such as `(x/170)**2.5` at x = -2. Clamp the base with `Math.max(0,x)`.
5. Render each wallpaper at the final resolution into `output/`, passing a crop of about 240 x 135 logical units around the focal point. For example: `node src/render.js 0 3840 2160 output/oil-lighthouse-sunset-3840x2160.png '' 70,150,240,135`. The empty `''` keeps the scene's own seed. Read the crop it prints to check the brushwork or the cut edges at 1:1.
6. Deliver the finished files from `output/`:
   - Name them `<style>-<scene>-<width>x<height>.png`, for example `papercut-lakeside-cabin-3840x2160.png`.
   - Name seed variants `…-seed<N>-…` and texture variants `…-tseed<N>-…`, for example `papercut-lakeside-cabin-tseed7-3840x2160.png`.
   - Delete the previews and crops.
   - Give the paths with a one-line caption. If a tool for sending files to the user is available, send the files with it too.
7. Offer next steps:
   - a new `--tseed=N` for different cut edges or brushwork on the same layout
   - a new seed for a different layout of stars, clouds and scattered details
   - the same scene in the other style
   - another aspect ratio, which needs the composition redone for the new W
   - a palette change, or a new scene variation (time of day, focal side)

## Notes

- An oil PNG is about 19 MB at 4K and 70 MB at 8K; a paper-cut PNG is about 10 to 13 MB at 4K. If the user wants something smaller, give the output a `.jpg` name and `render.js` writes a JPEG at quality 92.
- To reproduce an image exactly, keep the same scene, `seed`, `tseed` and W, and the same browser (the Chrome fallback can differ slightly from bundled Chromium). Seeds do not reproduce images made before the texture seed existed, because the texture used to continue the build's random sequence.
- `scripts/test.js` checks the shipped assets end to end (`NODE_PATH=<dir with playwright> node scripts/test.js`). Run it after changing anything in `assets/`.
