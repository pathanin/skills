# HTML deck format

One file, `DECK/index.html`, on a fixed 1280×720 stage that `deck.js` scales to the window.
Everything below is what the review toolbar, the QA check and the PPTX writer understand.
Write new slides only in this vocabulary, with **inline styles in px**.

## Slide

```html
<section class="slide" id="s3" data-title="Three steps" style="background:#FFFFFF"> … </section>
```

- `id="sN"` is the slide's position (1-based). Review comments and edits are keyed by it, so after
  deleting, copying or reordering sections run `deck_tool.py renumber DECK`.
- `data-title` is a human label (the slide's title text).
- `style="background:…"` takes a colour, a `linear-gradient(…)`, or, on converted decks, the
  layout picture (`#FFF url(media/x.png) center/100% 100% no-repeat`).
- Converted decks add `data-src="k"` (source slide k) and `data-layout="<layout name>"`. Keep both
  when editing. When you copy a section, the copy keeps them, and the export builds that copy fresh on the
  same layout. A section without `data-src` is built fresh on `data-layout` (or a blank layout).

## Elements (direct children of the section)

Every element is absolutely positioned: `left/top/width/height` in px, inline. Every element has a
`data-name`, unique on its slide, which becomes the PowerPoint shape name. Converted shapes also carry
`data-id`, the source shape id. Never invent or copy a `data-id`: leave it off new elements, and remove it
from an element you duplicate.

| Element | Markup | Exports as |
|---|---|---|
| Box / card / badge | `<div class="sh" data-name="Card 3" style="…;background:#F4F6FB;border:1px solid #DDE3EF;border-radius:16px">` | rectangle; rounded rectangle when `border-radius` is in px; ellipse when it is `50%`. `box-shadow` becomes a shadow. |
| Text | a `.sh` containing `<div class="tx" style="padding:…;justify-content:flex-start|center|flex-end">` with `<p>`/`<span>` | text box, or text inside the shape. `justify-content` is the vertical anchor. |
| Picture | `<div class="pic" …><img src="media/x.png" alt=""></div>` | picture (`border-radius` → rounded / oval) |
| Cropped picture | `<div class="pic crop" …;overflow:hidden"><img style="position:absolute;width:W%;height:H%;left:-L%;top:-T%"></div>` | cropped picture |
| Clip | `<div class="pic vid" …><video src="media/c.mp4" poster="media/p.png" preload="none" playsinline></video><img class="poster" src="media/p.png" alt=""></div>` | embedded movie, plays on entry, loops |
| Table | `<table class="tbl" … style="left;top;width;height:auto"><colgroup><col style="width:…">…</colgroup><tr style="height:…"><td style="padding;vertical-align;background;border-bottom:1px solid #…"><div class="cell"><p>…</p></div></td>…` | table (no table style; fills and borders per cell; `colspan`/`rowspan` merge) |
| Preset shape | `.sh` with `data-prst="triangle"` and an inline `<svg class="svg">` | that PowerPoint preset |
| Line / arrow | `.sh` with `data-prst="line"` and `<svg><line x1 y1 x2 y2 stroke stroke-width marker-end>` | straight connector |
| Master artwork | `data-layer="master"`, no `data-name` | not exported (PowerPoint draws it from the layout); not editable or animated |

## Text

```html
<p style="text-align:left;font-size:22px;line-height:34px;margin-top:14px">
  <span style="font-size:22px;font-weight:700;color:#0F1B3D">Bold lead</span><span style="font-size:22px;color:#1B2233"> rest of the sentence</span>
</p>
```

- Put `font-size` on every `<p>` and `<span>`, and colour on every span. The writer reads spans, not inheritance.
- Use `line-height` in px for an exact spacing; a unitless value is a multiple of the font's normal line height.
- Space paragraphs with `margin-top` / `margin-bottom`. Use `<br>` for a line break inside a paragraph.
- Bullets go on their own span: `<span class="bu" style="…;color:#2F6BFF">● </span>`. Give the paragraph
  `padding-left:28px;text-indent:-28px` for a hanging indent. The export makes it a real PowerPoint bullet.
- `white-space:pre-wrap` is on, so spaces count. Never letter-space Thai text.
- The bundled font is the CSS family `"DeckFont"` (set in deck.css). Don't name other fonts in inline
  styles: they are not bundled, the QA check can't see them, and the export uses the deck font anyway.

## Don'ts

- No per-element animation classes or attributes on `.sh` / `.pic` / `.tbl`. `deck.js` animates them in reading order by itself.
  Explanatory motion goes in a `.fx` layer, described below.

## Motion layer (`.fx`, HTML only)

Use it for motion that explains something, such as a packet travelling a path, a line drawing itself,
a ripple, a highlight moving down a list, or a stamp landing.

```html
<div class="fx" aria-hidden="true" style="left:0;top:0;width:1280px;height:720px">
  <svg width="1280" height="720">…paths, circles…</svg>
  <div class="dot" style="--p:path('M100 200 L400 200');--t:3s;--dl:1s"></div>
</div>
```

- Put it last in the section, with **no `data-name`**. Without a name, the PPTX export, the review
  toolbar and `deck.js` entrance animation all ignore it. A full-slide box is also skipped as a background.
- Put the keyframes in one `<style id="fx-css">` in `index.html`'s head, and scope every rule as
  `.slide.anim .fx …`. `deck.js` re-adds `.anim` each time a slide is shown, so the motion restarts on
  every visit. It never sets `.anim` in `?shot`, `?qa`, `?flat`, print or reduced motion, so screenshots
  show the static frame.
- The static frame must read on its own. Keep motion-only parts (`.dot`, flow dashes) at `opacity:0`
  outside `.anim`, and start custom motion after about 0.9 s so the entrance rise finishes first.
- Animate children inside the layer, never the `.sh` wrappers, which `deck.js` transforms.
- Prefer CSS (`offset-path`, `stroke-dashoffset`, `transform`) over SMIL `<animate…>`. SMIL starts at page
  load and keeps running in screenshots.
- Keep every word in `.sh`/`.tx` boxes. Text inside `.fx` can't be edited and isn't checked for overflow.
- Vary the effect with the idea, and don't use the same one on every slide.
- To check motion, the screenshots won't help, because they are static. Load the page without `?shot` in
  a headless browser and capture after 2–3 s.
- No external URLs, CDNs or web fonts. The deck must work offline over `file://`.
- No flexbox/grid layouts *between* elements. Position each one. Flex is only used inside `.tx`.
- Keep text inside its box. `shoot.mjs DECK --qa` lists boxes whose text overflows; fix anything over about 2 px.
