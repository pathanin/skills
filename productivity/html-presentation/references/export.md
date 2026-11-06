# Export internals, checks and gotchas

## PPTX: stage 1, `export.py` (python-pptx + lxml)

**Converted decks** (`deck.json` has `"source"`):

- `html_diff.py` compares `index.html` with `.source/baseline.html`, the untouched conversion. Never edit
  the baseline. Slides are matched by `data-src`, shapes by `data-id`.
- Unchanged shapes keep the source XML exactly: layouts, notes, charts and clips. Source animations survive stage 1 too; on Windows, stage 2 replaces them with its own.
- What happens to each kind of change:

| Change in the HTML | What the export does |
|---|---|
| text only | Paragraphs are rebuilt with the shape's own `pPr` and `rPr` as templates, so font, bullets and spacing survive. |
| moved or resized | The `xfrm` is updated. A shape inside a group is rebuilt. |
| restyled (class, inline style, picture source) | The shape is deleted and rebuilt by `pptx_writer`. |
| deleted | The shape is removed, and media rels no one uses are dropped. |
| added (no `data-id`) | Built by `pptx_writer` and placed after its HTML predecessor in the stacking order. |

- A changed slide `background` (colour or gradient) is set on the slide. A changed background picture is not
  exported (warning): pictures come from the layout.
- Moving an existing shape up or down the stacking order (reordering elements in the HTML) is **not**
  exported; only added or rebuilt shapes take their HTML position.
- Slides follow the HTML order, and source slides that are no longer used are dropped. A section without
  `data-src`, or a second copy of one, is a new slide:
  - It uses the layout named by `data-layout`, else the copied slide's layout, else a blank layout.
  - Its placeholders are removed.
  - Everything on it is built from the HTML.

**New decks** (no source) start from a blank 16:9 `Presentation()`, and every slide is built from the HTML.

`pptx_writer` maps the format in `format.md`. Anything it can't express goes into the warnings list at
the end of the run, for example a gradient with more than 2 stops (it keeps the first and last) or a freeform shape (it becomes the bounding rectangle). Read the warnings.

## PPTX: stage 2, `export_anim.ps1` (PowerPoint through COM, Windows only)

- Every shape except a full-slide background gets one entrance effect, With Previous. The delays follow the
  same reading order as `deck.js`: `min(650, (top-50)*0.85 + left*0.08)` ms.
- Text and small shapes Float In (Ascend) over 0.5 s. Pictures, clips, big panels and tables Fade over 0.6 s.
- Clips play on entry, muted, and loop.
- The deck is saved with `SaveAs(out, 24, -1)`, which embeds the fonts.
- **Gotchas** (already handled in the script; keep them if you change it):
  - Pass enum values as ints from `[int][Enum]::Parse(...)`. Enum objects from the reflection-loaded
    PIA arrive as defaults: Appear, After Previous.
  - Set clip `AnimationSettings.PlaySettings` *before* adding the effects. It is the legacy API, and it
    rewrites existing effects as plain Appear.
  - PlayOnEntry adds its media effect After Previous. The script re-times it to With Previous at the
    clip's own delay.
- If PowerPoint is missing, the stage fails, or the platform is not Windows (macOS PowerPoint has no COM),
  the stage-1 deck is written without animation or embedded fonts, and the run says so. Clips then need a
  click to play, and `--render` writes nothing.

**HTML-only touches:** tables reveal row by row in HTML but fade as one shape in PowerPoint.
Slide transitions are not exported.

## PDF

`shoot.mjs DECK --pdf FILE`: headless Edge/Chrome prints `?flat`, one 1280×720 page per slide, with
clips shown as their posters and animation off.

## Checks after an export

1. `python <skill>/scripts/check_anim.py OUT.pptx`: every effect should be `withEffect`, with one auto-start group per
   slide and a longest reveal of about 1.2 s or less.
2. Windows only: pass `--render DIR` to the export, which saves PowerPoint's own PNG of each slide. Then run
   `node <skill>/scripts/shoot.mjs DECK SHOTS` and `python <skill>/scripts/compare.py SHOTS DIR SIDE`, and look at the `SIDE` images.
   - Scores up to about 5/255 are text smoothing.
   - Anything higher needs a look, though wrapping differences in long Thai lines are normal.
3. If the pptx skill is installed, run its `scripts/office/validate.py OUT.pptx --original DECK/.source/source.pptx`.
   It is slow on big decks, so run it once at the end.

## Converter limits (`convert_pptx.py`, run once by `init_deck.py --from`)

- **Fonts:** one font family per deck, the one most of the slide text uses. It is bundled as
  `fonts/*.ttf` (a face inside a macOS `.ttc` collection is extracted to its own file). Runs in other fonts render in it. Pass `--font` to choose another.
- **Inherited styles are resolved:** master text styles → master/layout placeholder → shape list style →
  paragraph. Table styles from `ppt/tableStyles.xml` are resolved as well. Theme effects (glow, 3-D) are dropped.
- **Shapes:** presets other than rect, roundRect, ellipse, line, triangle, arrows, chevron, star, diamond and
  parallelogram are drawn as their bounding box. `--qa` lists them.
- **Not converted:** charts, SmartArt and OLE objects become a hatched placeholder box. In the
  export they keep the source XML as long as the placeholder is not edited.
- **Groups** are flattened in the HTML (the children keep slide coordinates). A text edit inside a
  group is applied in place. Moving or restyling a grouped shape rebuilds it outside the group.
- **Slide size:** 16:9 sources map 1:1. Other sizes are stretched to 1280×720 (init warns).
