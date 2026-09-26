# Rigging characters and jointed objects in SVG

## 1. Read the sheet into numbers

- Run `probe` with `--pick` on the fills, shadows, line colour and eye colour, and `--crop` on the face and hands.
- Measure with `probe --bbox=x,y,w,h` around each view (leave background all around the figure): it prints the exact extent and bottom centre. Measure the head the same way with a box around the head alone, or read it off a `--crop`.
- Draw the character in the sheet's own pixel units, with the origin at a landmark you measured, usually the bottom centre between the feet of the front view. Then every number you read off the sheet goes straight into the markup, and scale comes from one `s` on the root group.
- Pick the unit: the head height. Every proportion note ("3.2 heads tall") becomes a pixel length on the sheet.
- Line weight is a fraction of the head height on the sheet. Use the same fraction on stage, with `stroke-linejoin="round"` and `stroke-linecap="round"` unless the style is sharp.

## 2. Pick the rig style that fits the design and the beats

| Rig | When it fits | How |
|---|---|---|
| **Cut-out** (rigid parts on pivots) | Most flat or vector characters, mascots, paper styles | One `<g>` per part, nested parent to child, each rotated about its joint with `M.tf` |
| **Rubber hose** (stroked limbs) | Bendy, cartoony and 1930s styles, simple mascots | Each limb is one `<path>` whose `d` is rebuilt every frame, from shoulder through a bend control point to the hand. The hand and foot are cut-out parts placed at the end |
| **IK limbs** | Feet that must stay planted, hands that reach for an object | `M.ik2` gives two bone angles from the root and a target point. Use it with either style |
| **Shape morph** | Squishy blobs, faces, mouths, simple expressions | The same path structure in every key shape, blended with `M.kf` or `M.mix` on the `d` string |
| **View swap** | Turns between turnaround views | One group per view, swapped on a blink or on a fast move, so the switch is not noticeable |
| **2.5D feature shift** | Small head turns without drawing a new view | Shift the eyes, nose and mouth across the head by `yaw*headWidth*k`, and squash the features near the edge |

Combine rigs freely. A cut-out body with rubber-hose arms and a morphing mouth is common.

Raster parts (per-layer PNG exports of painted art) rig the same way: put each `<image href="../refs/arm.png" x y width height>` inside its own `<g>` and pivot the group. They load before the first frame. Supply them at 2× their size on stage, or they soften in the final render.

## 3. Build the hierarchy

```
root (placement on stage, walk and jump offsets)
└ hips
  ├ torso ─ neck ─ head ─ { brows, eyes (white, pupil, lid), mouth set, ears / hair chain }
  │        ├ upperArm.L ─ foreArm.L ─ hand.L
  │        └ upperArm.R ─ foreArm.R ─ hand.R
  ├ thigh.L ─ shin.L ─ foot.L
  └ thigh.R ─ shin.R ─ foot.R
```

- Draw each part in its own local coordinates, in its rest pose, with the joint at a known point. Record that point as the part's pivot `(ox,oy)`.
- Nest the groups so children inherit their parent's motion. `M.tf(el,{r,ox,oy})` rotates a part about its pivot in its own coordinates.
- Draw order fights the hierarchy: the far arm must be behind the torso, yet it is a child of the shoulder. Fix it with one of these:
  - Put the far limbs in a separate group placed before the torso in the markup. Each frame, place that group at the shoulder: `const [sx,sy]=M.pointIn(torso,shoulderX,shoulderY,backLayer)`.
  - Or keep the limb nested and duplicate only the torso's front shape above it.
- Overlap the parts at every joint by the joint's radius, and put the pivot at the centre of the joint's circle. Rotation then never opens a gap.
- Give a part that holds props an attach point. Place the prop each frame with `M.pointIn(hand, gripX, gripY, world)`.

The skeleton of such a rig:

```js
stage.add(`<g id="hero"><g id="hips">
  <g id="torso"><path d="…"/>
    <g id="head"><path d="…"/><g id="eyeL"><ellipse …/><g id="lidL">…</g></g> … </g>
    <g id="armR"><path id="armR-hose" fill="none" stroke="#2b2b2b" stroke-width="14" stroke-linecap="round"/><g id="handR">…</g></g>
  </g></g></g>`);
// in render: pose from t
M.tf($('#hero'),{x:heroX,y:heroY});
M.tf($('#torso'),{r:lean,ox:0,oy:0});        // torso drawn with the hip joint at its local (0,0)
M.tf($('#head'),{r:headTilt,ox:0,oy:-120});  // neck joint at local (0,-120)
const ik=M.ik2(sx,sy,tx,ty,60,55,-1);        // shoulder to hand target, in torso space
const bend=[ik.jx,ik.jy];                    // rubber hose: quadratic through the elbow region
$('#armR-hose').setAttribute('d',`M${sx} ${sy} Q${bend[0]} ${bend[1]} ${ik.ex} ${ik.ey}`);
M.tf($('#handR'),{x:ik.ex,y:ik.ey,r:ik.a1+ik.a2});
```

`M.ik2` returns absolute angles measured from the +x axis. Subtract the angle each bone was drawn at: 90 for a limb drawn pointing down.

## 4. Faces and expressions

- **Eyes.** Draw the white, the pupil and a lid. The pupil moves for look direction, clamped inside the white: `M.clamp(dx,-r*.45,r*.45)`.
  - For a blink, scale the lid or the eye in y with the pivot at its centre.
  - Clip the pupil to the eye white with `<clipPath>`.
- **Brows.** Rotate and translate them. Brows carry most of the emotion.
  - Surprise: raised brows and wide eyes.
  - Anger: inner ends down, eyes narrowed.
  - Sadness: inner ends up.
- **Mouths.**
  - Either a set of shapes, one visible at a time. This suits lip sync and stylised faces.
  - Or one path whose key shapes share a structure, blended with `M.mix`. This suits smooth expression changes.
  - Build the set from the expression sheet.
- **An expression table.** A named pose is an object of parameters, for example `{browL:-8, browR:-8, lid:.6, mouth:'smile', pupilY:2}`. Blend between named poses with `M.mix(poseA,poseB,u)` and apply the result in one function.

## 5. Match the style

- Line: use the sheet's line colour, which is rarely pure black, and its weight ratio. Decide whether the line is a stroke on each part (it shows at the joints) or a single outline behind the whole silhouette (a thicker copy of the silhouette in the line colour).
- Shading: make a shadow shape in the shadow colour, clipped to the part with `<clipPath>` that references the part's own path. It then moves with the part. Rim lights work the same way.
- Texture and grain: an `feTurbulence` filter or a canvas grain layer. Keep the seed fixed per drawing, and change it on twos for boil.
- Trace check: with the character drawn in sheet pixels around the landmark `(fx,fy)` on the sheet, placed on stage at `(X,Y)` with scale `K`, and the sheet `SW×SH` pixels, the overlay lines up with
  `--ref-box=X-fx*K, Y-fy*K, SW*K, SH*K`.
  Render `stills --at=<a rest pose> --ref=refs/sheet.png --ref-opacity=.5 --ref-box=…` and fix the proportions until the silhouettes coincide. Where your art and the ghost of the sheet disagree, the sheet wins.

## 6. Test the rig before animating it

1. Render a range-of-motion stills row. In `render`, briefly drive each joint to its extremes, for example in a 2 s test scene.
2. Look for gaps at joints, wrong pivots, limbs flipping direction (IK `bend` sign), and draw-order errors.
3. Fix these before blocking the motion. A rig bug found during polish costs a full re-review.
