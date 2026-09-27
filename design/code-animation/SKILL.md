---
name: code-animation
description: Manual-only, invoked with /code-animation. Makes an animation entirely in code from the user's source materials (brand concept, character design or character sheet, storyboard or beat sheet, script, theme, music, visual references) using a shipped pipeline. The scene is SVG, Canvas and HTML written as a pure function of time; it is rendered frame-exact in headless Chromium, exported to MP4, GIF, WebM or ProRes, and reviewed with contact sheets and automatic QA. Use when asked to create, animate or render an animation, motion graphic, animated logo or logo reveal, character animation, explainer, title or intro sequence, kinetic typography, looping GIF, or animated short. Skip UI micro-interactions or CSS transitions inside an existing app's codebase, editing or converting an existing video, Blender or After Effects work, and static images.
argument-hint: "[brief and/or paths to source materials; optional duration, aspect, format]"
disable-model-invocation: true
---

# Code animation

You are the director and the animator. This skill is the studio: a fixed pipeline, already built and tested, so you never have to work out again how to render frames. Put your effort into what the materials mean and what the animation should be.

The creative decisions are yours: concept, staging, timing, style, and how each character moves and why. The materials set the constraints. Within them, take a clear point of view and commit to it. Don't settle for a generic or safe version of the brief. The engine gives you no taste and makes no choices for you.

## How the pipeline works

- `src/scene.js` is the only file you write. In `setup` it builds everything once: SVG markup, canvas layers and HTML text. In `render(t)` it sets every animated property from the time `t` alone.
- `src/stage.html` hosts the scene and exposes `seek(t)`. Opened in a browser, it is also a live preview with a scrubber.
- `src/render.js` seeks each frame in headless Chromium, screenshots it and pipes the PNGs to ffmpeg. Its other commands are the review tools.
- `src/motion.js` defines one global, `M`. It holds easing, keyframes, springs, noise, rig transforms, IK, path tools and text splitting.
- Every frame depends only on `t`. So any frame renders on its own, previews match the final render, and the review tools can sample any moment.

## Setup

1. Copy the engine into the working folder. If `${CLAUDE_SKILL_DIR}` is not an absolute path, or the copy fails, use the "Base directory for this skill" path shown when the skill loads.
   ```bash
   mkdir -p src output refs && cp "${CLAUDE_SKILL_DIR}"/assets/{stage.html,motion.js,render.js} src/
   ```
   If `src/` already exists from an earlier run, copy the three files again. Never overwrite `scene.js`.
2. Copy the user's materials into `refs/`, so the project is self-contained. Leave the originals where they are.
3. Check the environment once: `NODE_PATH=$(npm root -g) node src/render.js check`. Run every later command the same way, from the working folder.
   - `Cannot find module 'playwright'`: run `(cd src && npm i playwright)`, then drop the `NODE_PATH=` prefix.
   - Browser fails: `render.js` already falls back to installed Chrome. Run `npx playwright install chromium` only when both fail. Don't run it when `PLAYWRIGHT_BROWSERS_PATH` is set, because the browsers are preinstalled there and the error is something else.
   - `ffmpeg none` or `limited`: run `pip install imageio-ffmpeg`. On a PEP 668 system, add `--user` or `--break-system-packages`. `render.js` finds that ffmpeg by itself; `FFMPEG=/path` overrides it. Until then you can still write stills, sheets and PNG sequences.
4. Write review images (stills, sheets, studies, crops, previews) to your scratchpad by passing `--dir=<scratchpad>`. Otherwise they go to `$TMPDIR/code-animation`. `output/` holds finished files only.

## Workflow

### 1. Read the materials

Load `references/materials.md` and follow it for every material the user gave:

- View each image with Read.
- Run `render.js probe <image>` for its exact size and palette, `--pick=x,y` for exact swatch colours, `--bbox=x,y,w,h` for a figure's exact extent, and `--crop=x,y,w,h` to zoom in on details.
- Read PDFs page by page.
- Run `render.js sheet <video>` on video references to see them, and `qa` on them for their cut rhythm.
- Run `render.js audio <file>` on music or voice-over.

Write the findings into `plan.md` under **Reading**. For each material, list the hard facts to honour (hex values, proportions, fonts, beats, mandatory copy) and what they imply for motion. This step is the input for everything after it, so don't skip it or skim it.

When something is not specified, use these defaults and state them:

| Setting | Default |
|---|---|
| Aspect and size | 16:9 at 1920×1080. When a platform is named: 9:16 at 1080×1920 (Reels, TikTok, Shorts), 1:1 at 1080×1080, 4:5 at 1080×1350. |
| fps | 24 for character and cinematic pieces; 30 for motion graphics, brand, UI and type. For a hand-drawn look, keep the scene fps and step the drawings with `M.quantize(t,12)`. |
| Duration | Logo sting 3–5 s. Social loop 6–10 s. Explainer about 4–6 s per idea. Title sequence 10–20 s. Set to music: the track length. |
| Deliverable | MP4. Add a GIF when the user says GIF or web loop. Add a ProRes `.mov` with alpha when the animation is an overlay or will be edited further. |

Ask the user only in these cases:

- There is no subject at all.
- Two materials contradict each other on something that changes the whole piece, such as two different palettes for the same brand.
- A mandatory element is unreadable, such as copy in an image too small to read.

Otherwise decide, and note the decision in `plan.md`.

### 2. Write the treatment in `plan.md`

- **Concept**: one or two sentences giving the idea behind the piece, not a list of motions.
- **Format**: W×H, fps, duration, whether it loops, and the deliverables.
- **Motion language**: 3 to 6 rules, each traced back to a material. For example: "Everything enters from below on `outBack(1.2)`, from the brand's 'optimistic, upward' tone." or "Nothing rotates, because the character sheet shows a stiff, boxy robot."
- **Beat sheet**: a table of time range, what happens, focal point, and transition. When the user gave a storyboard, keep its beats and their order, and add timings, in-betweens and camera moves.
- **Cast and rig**: each character or moving object, its moving parts and pivots, and the views it needs.
- **Style frames**: the 2 to 4 moments that define the look.

In your first message, give the concept and format in 2 to 4 lines, then carry on. Don't wait for approval.

### 3. Build the look first, as style frames

1. Write `setup` with all the art, and a `render` that only places things at their style-frame poses.
2. Render the style frames with `stills --at=…` and review them with Read.
3. For a character or logo built from a reference, also render a trace check: `stills --at=<rest pose> --ref=refs/sheet.png --ref-opacity=.5 --ref-box=x,y,w,h`. The box that makes the overlay line up is in `references/rigging.md`.
4. Fix everything until the look matches the materials: exact palette hex, proportions against the ref overlay, line weight, and type.

Building the look before any motion keeps look bugs apart from motion bugs. Load `references/rigging.md` before you build a character or any jointed object.

### 4. Block the motion

Load `references/motion-craft.md`.

1. Write `render(t)` pose to pose. Put key poses at the beat-sheet times with `M.kf`, and hold them.
2. Get the timing right before you polish anything.
3. Review the whole piece with `sheet --n=12`, or `--n=16` when it runs over 10 s. Check that each beat reads at its time, that one thing leads the eye at a time, and that nothing moves across or covers text while it has to be read.

### 5. Polish

Add easing, overlap and follow-through, secondary action, camera moves and transitions.

Review every key action with `study --from=a --to=b --track=#marker`:

- The onion skin shows the poses and the arc.
- The dots mark one position per frame. Even spacing reads as mechanical, bunched dots at the ends read as eased, and dots that jump apart are a pop.

Tracking a joint needs a tiny marker at that point: `<circle id="trk-hand" r="1" fill="none"/>` inside the hand's group.

### 6. Preview and QA

1. Run `video --out=<scratchpad>/preview.mp4 --scale=.5 --qa`.
2. Compare every reported **hold** and **jump** against the beat sheet:
   - An unplanned hold is dead air. Replace it with a moving hold, such as breathing, drift or a slow push-in.
   - An unplanned jump is a pop: a missing ease, a `display` toggle, a shot seam, or a motion that starts or stops at full speed.
   - A hold reported during a moving hold means the moving hold is too subtle to see.
   - Planned cuts and planned holds are fine.
3. For a loop, add `--loop`. QA then plays the file twice and reports whether the seam is smooth or pops.
4. You can't watch the video. The sheet, the studies and QA are your eyes, so run them after every significant change.

### 7. Final render and delivery

Don't start the final render until each of these that applies has been done. These steps are what stand in for watching the video, so skipping one means shipping unseen work:

- `plan.md` has the Reading, the treatment and the beat sheet.
- Style frames were reviewed with `stills`.
- Anything rebuilt from a reference image (a character, a logo) passed a `stills --ref` trace check.
- Each key action (a walk, a jump, a wave, a reveal) was reviewed with `study`, and planted feet read `0.0` while planted.
- The whole piece was reviewed with `sheet`.
- The preview passed `qa` (with `--loop` for a loop), or each reported hold and jump is one you planned.

Plan the render's time before starting it: frames × the per-frame cost in the Speed note × the `--mblur` factor. Leave `--workers` at its default; parallel pages produce frames identical to a single page's.

- The Bash tool gives up waiting after 2 minutes by default. For a render estimated at up to about 9 minutes, pass the tool's `timeout` at its maximum (600000 ms) and run it in the foreground.
- For a longer render, run it in the background, then keep checking it within this same reply until it exits. The progress lines include the time remaining.
- Never end your reply while a render is still running. Its file is truncated until it finishes, and nothing brings you back to deliver it.

1. Render into `output/`, named `<project>-<W>x<H>.<ext>`:
   - `video --out=output/<name>.mp4`
   - Add `--mblur=8` when there are fast moves: whip pans, spins, or objects crossing more than about 40 px per frame.
   - Sound comes from `SCENE.audio`, or `--audio=refs/<track>` to override it.
   - Add a GIF with `video --out=output/<name>.gif --width=640 --fps=25` (add `--colors=64` if it is over about 5 MB), and a `.mov` for alpha when needed. ProRes 4444 runs to about 60 MB per second at 1080p; when the file has to travel by chat or email, add `--codec=png`.
2. Run `qa` on the final render, and `sheet output/<name>.mp4` to look at the encoded file itself.
   - Social platforms and chat previews show the first frame as the thumbnail. If frame 0 is empty or dark, either open on a readable frame or export a poster: `stills --at=<hero moment> --dir=output`, and say which it is.
3. Deliver:
   - Give the paths with a one-line caption. Send the files too if a tool for sending files is available.
   - Mention the live preview: `python3 -m http.server` in the working folder, then open `/src/stage.html` (it does not work from `file://`).
   - Delete the previews.
4. Offer next steps: another aspect ratio (which needs a new composition), alternate timing or palette, a loop version, other formats, or a new pass on one beat.

## The scene contract

```js
const SCENE={
  width:1920, height:1080, fps:30, duration:8,
  background:'#f4efe6',                  // or 'transparent' for alpha output (.webm .mov .gif, PNG frames)
  audio:'../refs/track.wav',             // optional soundtrack: plays in sync in the live preview; video muxes it (--audio=none to skip)
  async setup(stage){ /* build once: stage.add(svgMarkup), stage.canvas(), stage.html, stage.font(), refs from ../refs/ */ },
  render(t,stage){ /* set every animated property from t */ },
};
```

`PARAMS` holds the values passed with `--set=k=v,k2=v2`, and is readable while `SCENE` is being defined. Use it for variants of one scene instead of copying it: `background: PARAMS.alpha ? 'transparent' : '#f4efe6'`, then `video --set=alpha --out=output/x-alpha.mov`.

Hard rules. Breaking any of them makes frames differ between the sheet, the preview and the final render:

1. `render(t)` sets every animated property from `t` on every call. Never carry state from one call to the next, such as `x+=v`. Frames render out of order: sheets, studies, motion-blur subframes and seeking back.
2. Never use `Date`, `performance.now`, timers, `requestAnimationFrame` or CSS transitions. For randomness, use `M.rng(seed)` in `setup` and `M.hash(i,seed)` or `M.noise` in `render`. (The harness seeds `Math.random` as a safety net, so a stray call stays reproducible, but a stray call in `render` still re-rolls every frame.)
3. CSS `@keyframes` and `element.animate()` are fine: the harness pauses them and sets `currentTime` to `t`. Libraries are not shipped: install them with `(cd src && npm i <lib>)` and `await import('./node_modules/…')` in `setup`, rather than from a CDN, which sandboxed networks often block. GSAP: `({gsap}=await import('./node_modules/gsap/index.js'))`, build timelines paused, and call `tl.seek(t)` in `render`.
4. Anything stateful, such as physics, flocking, particle collisions or cloth, is simulated in `setup` into arrays of samples (at the scene fps or finer, with substeps for stability). `render` reads them with `M.sample(samples,t,rate)`, which interpolates between samples, so motion-blur subframes and a higher `--fps` stay smooth.
5. Create every element in `setup`, and hide it with opacity or `display` until it is needed. Creating elements inside `render` leaks. Canvas layers are the exception: clear them and redraw every frame.
6. `M.tf` replaces an element's whole `transform`. So animate a wrapper `<g>`, and keep any transform the artwork has on the elements inside it.
7. For a loop, make every motion periodic in `duration` (`M.loop`, or `Math.sin(M.TAU*t/duration)`), so the frame at 0 equals the frame at `duration`.
8. Give backgrounds a bleed past W×H wide enough for the largest camera pan, zoom-out or shake, or the stage edge shows.

### Which layer to use

| Layer | Use it for |
|---|---|
| SVG (default): `stage.add(markup)` | Characters, logos, shapes, lines, masks, clip paths, gradients, filters. Sharp at any size, and groups nest into rigs. |
| Canvas 2D: `stage.canvas(name,'under' or 'over')` | More than about 300 moving pieces (particles, rain, confetti), per-pixel texture and grain, generative trails. |
| HTML: `stage.html` | Typography: real text layout, per-letter spans with `M.split`, CSS filters and blend modes. |
| WebGL: `stage.canvas(name,'over','webgl2')` | Only when real 3D or shaders are the point. Get the context with `preserveDrawingBuffer:true` (for three.js: `new THREE.WebGLRenderer({canvas, preserveDrawingBuffer:true, alpha:true})`, `setPixelRatio(stage.dpr)`, `setSize(W,H,false)`, and call `renderer.render` inside `render(t)`). three.js: `(cd src && npm i three)`, then `await import('./node_modules/three/build/three.module.js')`. Headless rendering is software WebGL, so keep scenes modest. |

The stacking order, back to front: canvas `'under'`, SVG (parallax layers deeper than 1, `world`, nearer layers, then `screen`), canvas `'over'`, HTML, then the `--ref` overlay.

### stage

| Member | What it does |
|---|---|
| `W H fps duration frames dpr t frame` | Scene metrics and the current time |
| `svg defs world screen html el` | The root SVG and its `<defs>`; `world` (moved by the camera); `screen` (SVG that ignores the camera, for titles and UI); the HTML layer; the stage div |
| `add(markup, parent=world)` | Inserts SVG markup and returns the first element added |
| `await load(url, parent=world)` | Inserts a supplied SVG file (logo, character art) as live markup and returns its `<svg>`. Its `<style>` rules are scoped to that copy, and ids that collide with ones already on the stage become `<file>_<n>__<id>`. Position it with `x y width height` on the returned `<svg>`, and wrap the parts you animate in new `<g>` elements (hard rule 6) |
| `$(sel)` `$$(sel)` | `querySelector` and `querySelectorAll` inside the stage |
| `canvas(name, where='over', type='2d')` | A hi-DPI layer drawn in stage units, with `ctx.clear()` |
| `camera({x,y,zoom,r})` | Centres `world` on (x, y). Neutral is `{x:W/2, y:H/2, zoom:1, r:0}` |
| `layer(depth, name?)` | A parallax group the camera moves at 1/depth of its pan, zoom and roll: `depth` 3 for far hills (behind the world), 0.5 for foreground leaves (in front). Pass it as the `parent` of `add` |
| `font(family, url, {weight, style})` | Loads a font file supplied with the materials. Await it in `setup`. Pass the file's weight (`{weight:'700'}` for a Bold file), or text set in that weight gets a faux-bold |
| `webfont(family, [weights], ital=false)` | Loads a Google Font by name before the first frame (needs network). Await it in `setup` |
| `image(url)` | A decoded `Image`, for drawing to a canvas |

Asset URLs resolve from `src/`, so the materials are at `../refs/<file>`.

### M (motion.js)

| Area | Functions |
|---|---|
| Maths | `clamp lerp invLerp remap smoothstep deg rad TAU` |
| Easing (`M.ease`) | Single names: `linear`, and `in`, `out` or `inOut` joined to `Quad Cubic Quart Quint Sine Expo Circ Back Elastic Bounce`, as in `M.ease.inOutSine` or `M.ease.outBack`. Factories: `back(s)`, `elastic(amp,period)`, `bezier(x1,y1,x2,y2)`, `steps(n)`, `spring(z)`. Presets: `css`, `material`, `snappy`, `anticipate`. A name that does not exist throws and lists the real ones |
| Time | `seg(t,t0,t1,ease)` gives progress 0..1. `stagger(t,i,start,each,dur,ease)`. `shots(t,[durs])` gives `{i,t,u}`. `quantize(t,12)` steps the drawings. `loop` and `pingpong` |
| Values | `kf(t,[[time,value,ease?],…])` for pose-to-pose (a key's ease shapes the segment arriving at it). `spline(t,keys)` passes smoothly through the keys. `mix(a,b,u)` handles numbers, arrays, objects, `#hex` (blended in OKLab) and same-shape path strings (morphs). `color(a,b,u)` |
| Physics | `sample(samples,t,rate)` reads a simulation baked in `setup`. `spring(t,freq,z)` for a damped settle 0 to 1. `arc(u,p0,p1,h)` for a thrown arc. `squash(k)` gives `[along,across]` with the area kept |
| Random | `rng(seed)`, with `.range .int .pick`. `hash(n,seed)`. `noise(x,seed)`. `wiggle(t,freq,amp,seed)` |
| DOM | `svg(tag,attrs,parent)`, `html(…)`, `set(el,attrs)` |
| Rig | `tf(el,{x,y,r,s,sx,sy,sa,skx,ox,oy,o})` transforms about the pivot `(ox,oy)`, with `sa` as the squash axis and `o` as opacity. `ik2(ax,ay,tx,ty,l1,l2,bend)` is two-bone IK. `pointIn(el,x,y,target)` maps a local point through the rig |
| Paths | `trim(path,start,end)` draws a stroke on or off. `along(path,u)` gives `{x,y,a}` for following a path |
| Text | `split(htmlEl,'chars' or 'words')` returns spans to stagger, in reading order. It keeps `<br>` and inline markup, and never breaks a line inside a word |

### render.js

Every command takes `--scene=src/other.js` (another scene), `--set=k=v,…` (a variant of this one, see `PARAMS`), `--dir=`, and `--timeout=s` (default 60: a single frame taking longer is reported as a hang). Options always take `=`; an unknown option or a stray argument stops the command and lists the valid options.

| Command | What it does |
|---|---|
| `check` | Checks Playwright, the browser and ffmpeg |
| `video --out=file` | Renders the video. The extension picks the format: `.mp4` (H.264), `.webm` (VP9, with alpha if the background is transparent), `.mov` (ProRes 4444 with alpha; `--codec=png` makes a lossless PNG-in-MOV several times smaller, which every editor also reads), `.gif` (palette + ordered dither; `--colors=N` caps the palette to shrink the file), or `folder/` (PNG frames). Options: `--scale=k`, `--width=N` or `--size=WxH`; `--fps=N`; `--from=s --to=s`; `--mblur=N` (N subframes, 180° shutter); `--audio=file`; `--workers=N` (parallel pages, default CPU count − 1, at most 4; the frames are identical to one page's); `--qa`; `--loop` for a loop (QA checks the seam, and motion-blur subframes wrap around it) |
| `stills --at=0,1.5,f90` | One PNG per time, given in seconds or as `f<frame>`. Options: `--scale`, `--ref=img --ref-opacity=.5 --ref-box=x,y,w,h` |
| `sheet [<video>] [--n=12] [--from --to]` | A labelled contact sheet of evenly spaced frames, of the scene or of any video file (a reference, or your encoded output) |
| `study --from --to [--n=8] [--track=#a,#b]` | Onion skin of the moving parts, plus a dot per frame for each tracked element, with the spacing listed in stage units |
| `probe <image> [--pick=x,y;x,y] [--bbox=x,y,w,h;…] [--bg=#hex] [--crop=x,y,w,h] [--colors=12]` | Size, palette with shares, exact pixel colours, the exact extent of whatever is not background inside each region, and a zoomed crop. The background is the image's most common colour (transparent for a mostly transparent image) unless `--bg` says otherwise, so a horizontal slice through a figure measures just that part |
| `qa <video> [--loop]` | Holds of 0.4 s or more, and jumps (a frame that changes far more than both its neighbours), with timecodes. `--loop` also checks the seam from the last frame back to the first |
| `audio <file> [--json=src/audio.json] [--fps=30]` | Duration, tempo and beat grid, the strongest hits, loudness per second, and energy jumps. `--json` also writes per-frame `level`, `low` (bass) and `high` (brightness) curves from 0 to 1, plus `beats` and `hits`, for motion that reacts to the sound. It is an estimate; timings the user gives win |

- The output size must keep the scene's aspect. For another aspect ratio, write a new scene (or branch on `W`) and recompose it; never stretch.
- Speed on 4 cores with 3 pages, encoding included: about 40 ms per frame at 720p, 70 ms at 1080p and 280 ms at 4K, plus 1–2 s of start-up, so a minute of 1080p30 takes about 2 minutes. `--mblur=N` multiplies that by N; heavy SVG filters and WebGL are slower. A `PAGE ERROR` or `scene threw at t=… (frame N)` message names the failing frame; reproduce it with `stills --at=fN`.

## Known problems

| Symptom | Cause and fix |
|---|---|
| `WARNING: the frame at …s changed after seeking elsewhere` | `video` and `sheet` render one frame twice, with a seek in between and on two pages, and they differed: state carried across `render` calls, a clock, or setup that differs per page. Frames will flicker. See hard rules 1 and 2. |
| A part swings around the wrong point | The pivot `(ox,oy)` is in the part's own drawing coordinates, before its transform. Measure it on the art. |
| Gaps open at joints when limbs rotate | Overlap the parts by the joint radius, with round caps, and put each pivot at the centre of the joint circle. |
| A transform in the markup is lost | `M.tf` overwrote it. Wrap the art in a `<g>` and animate the wrapper (hard rule 6). |
| A morph snaps instead of blending | The two path strings differ in commands or number count, so `M.mix` switches at u = 0.5. Author both shapes with identical structure. |
| `warning: FONT FALLBACK: "X" is not available` | The scene names a font the browser does not have, so that text renders in a substitute. Load it in `setup` with `await stage.font(family,url)` (a supplied file) or `await stage.webfont(family,[weights])` (Google Fonts), or pick an installed font (`fc-list : family`) and name the substitution. |
| Camera moves reveal the stage edge | The background has no bleed (hard rule 8). |
| Motion looks mechanical | Linear spacing, everything starting at once, and no overlap. See `references/motion-craft.md`. |
| Fast motion strobes | Add `--mblur=8` to the final render, or draw smear frames for a cartoon style. |
| A GIF is huge or banded | Keep it at 640–800 px wide, 20–25 fps and under about 10 s, and cap the palette with `--colors=64` (or 32). Glows and gradients cost the most, so prefer flat fills in art meant for GIF. |
| A raster logo or character is blurry in the render | You scaled up a small bitmap. Rebuild it as SVG (see `references/rigging.md`), or ask for the vector source when it's a logo. |

## Notes

- `scripts/test.js` checks the shipped assets end to end: `NODE_PATH=$(npm root -g) node scripts/test.js`. Its video, QA and audio checks need a full ffmpeg. Run it after any change to `assets/`.
- `evals/` holds a `claude plugin eval` suite (a brand logo sting, a raster mascot, a music loop). See `evals/README.md` before changing this file.
