# Reading source materials

Turn each material into two lists in `plan.md` under **Reading**:

- **Facts**: things you must honour exactly, such as hex values, proportions, fonts, mandatory copy, beats and logo rules.
- **Implications**: what the material suggests about motion. You choose which of these to act on, and the treatment records your choice.

## Procedure for any material

1. Copy it into `refs/` and view it with Read.
2. Get exact numbers for images; don't estimate colours or sizes by eye.
   - `render.js probe refs/x.png` gives the size and palette.
   - `--pick=x,y;x,y` samples swatches, fills, the line colour and the background.
   - `--bbox=x,y,w,h` gives the exact extent of a figure: a view on a model sheet, a head, the logo on an artboard.
   - `--crop=x,y,w,h` zooms in on hands, eyes, logo corners and small type.
3. PDFs: read them page by page. In brand guidelines, find the logo construction, clear space, colour values, typefaces, any motion or tone-of-voice pages, and the don'ts.
   - Use RGB or HEX values as given.
   - When only CMYK or Pantone values are given, convert them and mark the result as approximate in `plan.md`.
4. Video references: you can't watch them, so sample them.
   - Frame tiles: `ffmpeg -i ref.mp4 -vf "fps=2,scale=480:-2,tile=4x3" refs/ref-tiles-%02d.png`, then Read the tiles.
   - Editing rhythm: `render.js qa ref.mp4`. Its holds and jumps are the reference's holds and cuts.
5. Text briefs: pull out the platform, duration, must-show items, exact copy, CTA, audience and tone words.

## Brand concept and brand guidelines

**Facts**
- **Logo.** Use the SVG if one was supplied.
  - If you only have a raster, rebuild the logo as SVG paths, then check it with `stills --ref`. Never scale up a raster logo.
  - Keep the proportions, colours, clear space and minimum size as specified.
- **Palette** by role (primary, secondary, accent, background, text), with exact hex values.
- **Typefaces.** Load supplied font files with `stage.font`.
  - Otherwise use the nearest local font (`fc-list : family`) and name the substitution.
- **Don'ts.** The logo don'ts apply to motion too: no squash and stretch, recolouring, rotation or skew of the logo unless the guidelines allow it or the brand is plainly playful.
  - The logo's final frame must match the spec exactly, and hold for at least 1 s.

**Implications**
- How the logo is built suggests the reveal:
  - A mark built from circles or modules can assemble from its parts.
  - A monoline mark can draw on with `M.trim`.
  - A wordmark can stagger or mask letter by letter.
  - A negative-space mark can reveal through the space itself.
- The shape language suggests the transitions. A rounded brand suits soft wipes, blobs and irises; a geometric brand suits hard wipes, grids and slides.
- Tone words suggest the motion personality:

| Tone words | Timing | Easing | Amplitude and devices |
|---|---|---|---|
| calm, trustworthy, premium | slow moves, 600–1200 ms | `outCubic`, `inOutSine`, no overshoot | small distances, long holds, cross-fades and masks |
| playful, friendly, youthful | 300–600 ms | `outBack`, `ease.spring(.45)` | squash and stretch, bouncy stagger, arcs, overshoot |
| energetic, bold, sporty | 150–400 ms | `outExpo`, `snappy` | hard cuts on beats, big scale jumps, shake, motion blur |
| precise, technical, clinical | 250–500 ms | `material`, `inOutQuart`, some linear | a grid, orthogonal moves, trims and draws, no bounce |
| elegant, luxury | 800–1600 ms | `inOutQuart`, `inOutSine` | thin line draw-ons, slow masks, sparse elements, generous space |
| warm, handmade, organic | irregular | `outSine`, mixed | on twos (`quantize(t,12)`), line boil, `wiggle`, paper grain |
| mysterious, cinematic | slow, 1–3 s | `inOutSine` | slow push-ins (zoom 1 to 1.08), dark-to-light reveals, grain, long fades |

## Character design concept, character sheet, model sheet, turnaround, expression sheet

**Facts**
- **Proportions.** Measure the head height in pixels and express everything in heads: body height, and arm and leg lengths.
- **Construction shapes, palette and line.** Record the fill colours, the shadow and highlight colours, the line colour (often not pure black) and the line weight as a fraction of the head height.
- **Views drawn** (front, ¾, side, back), plus the expressions, props, and costume details that must survive.

**Implications**
- Weight and size set the timing:
  - Heavy or large characters get slower moves, longer anticipation, low bounce and a firm settle.
  - Small or light characters get quick, frequent motion with more overshoot.
- Personality sets how the character moves:
  - Nervous: jitter, frequent blinks, small fast moves.
  - Confident: big arcs and long holds.
  - Sleepy: heavy lids, drag, and late follow-through.
- Shape language sets the quality of motion. Round shapes move softly and bounce; squares are stable, stiff, and move in blocks; triangles are sharp, fast and angular.
- Build only the views and parts the beats need. If every shot is front-on, don't build a side view. See `rigging.md`.

## Storyboard, beat sheet, script, animatic

**Facts**
- The shots and their order, what each shows, the framing, dialogue or voice-over, and any timing notes and transitions.

**Implications**
- Translate it into the beat-sheet table with timecodes.
- If there are no timings, estimate them:
  - On-screen text: about 3 words per second plus 0.5 s.
  - Voice-over: about 2.5 words per second.
  - Actions: their natural durations (see `motion-craft.md`).
  - Add a hold after each important beat.
- Snap shot boundaries to frames. With music, snap them to beats.
- Keep the board's beats and order. You may add in-betweens, camera moves and transitions.
- When a panel is ambiguous, pick an interpretation and note it.
- Use each panel as a layout: where the focal point sits, the framing, and the screen direction. Recompose for W×H rather than stretching.

## Theme, mood or keywords only

You design everything:

- A palette of 4 to 7 colours with assigned roles.
- A shape language and a motion personality from the tone table.
- One specific idea.

Prefer a single specific image over a generic loop. "Autumn" could be one leaf's journey from branch to puddle, rather than falling-leaf wallpaper. Make style frames, then proceed.

## Visual references: moodboards, other animations, screenshots, art

- Extract the mechanisms, not the surface. Examples: "3-colour palette plus paper grain", "thick outline with the fill offset like a misregistered print", "the camera never moves; everything enters from the frame edges", "12 fps stepped motion", "hard cuts every 2 beats".
- Record 3 to 6 technique notes.
- Never copy distinctive characters, logos or artwork from a reference that is not the user's own.

## Audio: music, voice-over, sound effects

- Run `render.js audio refs/track.mp3` for the duration, tempo and beat grid, the strongest hits, loudness per second, and energy jumps (where a section starts or the track drops, snapped to the onset).
- Put the grid in the scene and time everything in beats: `const BEAT=60/bpm, B0=<first beat>, beat=n=>B0+n*BEAT;`. Snap shot lengths to beats and feed them to `M.shots`.
- The piece lasts as long as the audio unless the user says otherwise.
- Place events on the audio:
  - Land cuts on beats, or 1 frame early so they feel in sync.
  - Put accents on the strongest hits.
  - Put the big reveal on the largest energy jump.
- With voice-over, show each visual 0 to 4 frames before the word it illustrates.
- Mux the audio with `video --audio=refs/track.mp3`. A partial render (`--from`) starts the audio at the same point, so a preview of one section stays in sync.

## Conflicts and gaps

- When materials conflict, the user's latest words win, then brand guidelines, then the character sheet, then the storyboard, then references, then your own taste. Note every deviation in `plan.md`.
- A missing aspect, duration, fps or format takes the defaults in `SKILL.md`, stated in your first message.
