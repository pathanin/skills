# Motion craft in code

This is working knowledge to build on, not a set of templates. Each section gives the principle, the numbers that usually work, and how to express it with `M`. Break any of it when the concept calls for it.

## Timing

Frames at 24 fps (30 fps). These are starting points for normal-speed action; scale them by the character's weight and the piece's personality.

| Action | Duration |
|---|---|
| Blink: close 2 f, hold 0–1 f, open 3 f | 5–6 f (6–7 f) |
| Head turn | 8–12 f (10–15 f) |
| Anticipation before an action | 1/3 to 1/2 of the action's length |
| Hold, the shortest pose that reads | 6–8 f (8–10 f). An important pose: 12–24 f |
| Walk step (half a cycle), normal | 12 f (15 f). Brisk: 8–10 f. Slow: 16 f |
| Run step | 6–8 f (8–10 f) |
| UI or brand element entrance | 300–600 ms. Exit: about 70% of the entrance |
| Logo resolve and hold | 1.5–3 s to build, then 1 s or more of hold |
| Text on screen | 0.5 s + about 0.33 s per word, and at least 1.5 s |
| Stagger between siblings | 30–80 ms between letters, 60–120 ms between items |

- **Spacing is the motion's character.** Dots close together are slow and dots far apart are fast. Check them with `study --track`.
- **Moving holds.** A character must never be perfectly still. Keep a breath going, for example `sy=1+.012*Math.sin(M.TAU*t/3.2)` with the pivot at the feet, plus a slow `wiggle` sway of about 1°, and a blink every 2–5 s at irregular times.
- **Contrast in rhythm.** Fast against slow and busy against still. A beat reads when it comes after a hold.

## Easing vocabulary

| Situation | Easing |
|---|---|
| An object entering and settling | `outCubic`, `outQuart` or `outExpo`: fast in, soft land |
| An object leaving | `inCubic` or `inQuad`: accelerates away |
| Moving from one rest to another | `inOutCubic` or `inOutSine` |
| Settling with personality | `outBack` (overshoot about 10%) or `ease.spring(.4–.6)` (a wobble that settles) |
| Heavy, snappy, product-UI feel | `snappy` = `bezier(.16,1,.3,1)`, or `material` |
| Mechanical or constant | `linear`. Use it for rotation that keeps going, scrolling, conveyors and loops |
| Hand-drawn stepping | `steps(n)` on a value, or `M.quantize(t,12)` on the whole clock |

In `M.kf`, a key's ease shapes the segment arriving at that key. With `inOut` eases, motion stops at every key; that is pose-to-pose with a settle. To pass through a key without stopping (for arcs and camera paths), use `M.spline`.

## The principles, as code

- **Squash and stretch.** Stretch along the direction of motion at high speed, squash on impact, and keep the area constant.
  ```js
  const k=1+.25*speed01, [a,c]=M.squash(k);
  M.tf(body,{x,y,sx:a,sy:c,sa:velAngleDeg,ox:cx,oy:cy});
  ```
  Hold the squash for 1–2 frames at contact, then overshoot to a slight stretch as the object leaves. Never apply it to rigid objects or logos unless the style is plainly cartoon.
- **Anticipation.** Move a little the opposite way first: 10–30% of the main move's distance, taking 1/3 to 1/2 of its time. For example, `M.kf(t,[[0,0],[.25,-12,E.outSine],[.6,120,E.inOutCubic]])`.
- **Follow-through and overlap.** Parts do not stop together. A child part is the parent's motion delayed: `angle(t-i*delay)*falloff**i`, with a delay of 2–4 frames per link. Use this for hair, tails, ears, antennae, cloth corners and sleeves. Add an overshoot with `M.spring(t-tStop, 2.5, .35)` on each link.
- **Arcs.** Living things move in arcs. Get arcs from rotation about a pivot (natural for limbs), from `M.arc` for throws and jumps, and from `M.spline` through 3–5 points for paths. A straight line between two poses is a smell. Check it in the onion skin.
- **Slow in and slow out.** This is the default for anything with mass. Use constant speed only for mechanical things.
- **Secondary action.** Give a smaller motion that supports the main one: blinks during a head turn, a hand gesture while talking, a prop that jiggles. It should never compete with the primary action.
- **Staging.** Keep one centre of interest at a time. Stagger entrances so the eye travels, lead with the most important element, and keep the rest calm while something important moves.
- **Exaggeration.** Push the key poses 20–50% beyond realism. Code animation tends to look timid.
- **Solid drawing.** Keep volumes consistent through motion. A turning head keeps its size, and features move across the head rather than sliding off it.
- **Appeal.** Make the silhouette read clearly in every key pose. Check the key frames in the sheet as silhouettes.

## Recipes

These are starting points. Adapt them to the character and the concept.

**Bouncing ball**
- `M.arc(u,p0,p1,h)` for each hop, with `u` linear in time; gravity is built into the arc's shape.
- Each successive hop is about 60% of the previous height and about 80% of its duration.
- Squash 1–2 frames at contact, and stretch along the velocity near the contact.

**Walk cycle**, one step every 12 f at 24 fps. Place the key poses per step at contact, down, passing, then up.
- The body is lowest at *down*, just after contact, and highest at *up*. So the vertical bob runs at twice the step frequency: `y=bob*Math.cos(2*M.TAU*phase)`.
- Arms swing opposite to the legs. Hips and shoulders counter-rotate by 3–6°.
- The head bobs slightly behind the body (overlap).
- Planted feet must not slide: move the world or camera at the exact stride speed, or give each foot a world position that stays fixed through its stance and arcs to the next plant during its swing, and connect it to the hip with `M.ik2` or a stroked leg.
- Prove it with `study --track=#footL,#footR`: the spacing list must read `0.0` for every stance frame.

**Jump.** Anticipation crouch (6–8 f), launch stretch (2 f), arc (hang at the top: `M.arc` already slows there), landing squash (2–3 f), recovery overshoot, settle.

**Blink.** Scale the eyelid or eye to y ≈ 0.1 over 2 frames, then open over 3. Pair it with head turns and the start of a new thought.

**Lip sync.**
- Mouth shapes: rest, A/I (open), E (wide), O (round), U (small round), M/B/P (closed), F/V (teeth on lip), L (tongue).
- Change them on twos. Hit M/B/P closed exactly on the consonant.
- Lead the audio by 1–2 frames.

**Logo reveal**, choosing from the logo's construction:
- Trim-path draw-on, then a fill wipe.
- Parts assembling on staggered springs.
- A mask wipe through the negative space.
- A morph from a primitive shape: author the paths with the same structure.
- Particles converging, pre-simulated in `setup`.

End every reveal on the exact logo, and hold it.

**Kinetic type.**
- Split letters or words with `M.split`, then stagger y from 40–60% of the cap height with `outCubic` or `outBack`, plus opacity.
- Mask reveals line by line: put an `overflow:hidden` wrapper around each line and slide the text up out of it.
- Emphasise one word per phrase through scale, colour or weight.
- Keep the text still long enough to read it (see the timing table).

**Transitions.**
- Match cut: the same shape or position in both shots.
- Wipe in the brand's shape language.
- Whip pan: a camera move of more than 1.5 W in 4–6 frames, with `--mblur=8`.
- Zoom through an element into the next scene.
- Iris or shape mask.
- Hard cut on a beat.
- Use `M.shots(t,durs)` to find the active shot and its local time; show one shot group and hide the others.

**Camera.**
- Use `stage.camera({x,y,zoom,r})` with `inOutSine` or a spline path.
- Parallax: layers at depth d move at 1/d of the camera's speed. Put layers in separate groups outside `world`, or counter-transform them.
- Shake: `x+=M.wiggle(t,10,amp*decay)` and the same for `y`, with `r` at about a third of the amplitude in degrees. Let it decay over 0.3–0.6 s.
- Handheld drift: `M.wiggle(t,.3,4)`.

**Particles.**
- Make each particle a closed-form function of `(t-birth)`, using position = p0 + v·age + ½·g·age², plus a `wiggle` for drift, and lifetime-based opacity and size.
- Seed the birth times and velocities in `setup` with `M.rng`.
- Draw them on a canvas layer when there are more than about 300.
- If they must collide or interact, simulate them in `setup` and read the results with `M.sample`.

**Hand-drawn feel.**
- Animate on twos: `const tq=M.quantize(t,12)`, and feed `tq` to the character's motion while the camera stays smooth.
- Line boil: jitter the path points by ±0.6–1.5 px with `M.hash(Math.floor(t*8)*97+i,seed)`, or change an `feTurbulence` `seed` attribute at 8–12 fps on a displacement filter.
- Paper grain: a canvas layer of seeded noise, re-seeded on twos.

**Loops.** Make every motion periodic in `duration`. For a seamless idle loop, use sums of `Math.sin(M.TAU*k*t/duration+phase)` with integer `k`. Check the seam with `qa --loop`.
