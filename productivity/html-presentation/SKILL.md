---
name: html-presentation
description: Make and run a presentation as an HTML deck. Start it from an existing .pptx/template or from scratch. The user edits text in the browser and drops comment pins, and Claude applies them. Present it in the browser. When it is final, export it to an editable PowerPoint (native shapes, clips, entrance animations) and/or a PDF. Manual only; run it as /html-presentation [new <topic> | from <file.pptx> | review | export].
disable-model-invocation: true
argument-hint: "[new <topic> | from <file.pptx> | review | export]"
---

# HTML presentation

In this workflow `DECK/index.html` is the source of truth from the first day to the last:

1. **Start:** convert an existing PPTX, or scaffold a new deck and write the slides.
2. **Loop:** the user edits wording in the browser (**E**) and drops comment pins (**C**) for anything
   else. Claude applies the edits and answers the comments.
3. **Present:** open the HTML deck in a browser.
4. **Finalize:** export PPTX and/or PDF when the user asks. Exports are outputs: never edit them by hand.
   Re-export after changes.

`<skill>` below is this file's folder; scripts are in `<skill>/scripts`. Works on Windows and macOS.
Needs Python 3 with `python-pptx lxml fontTools pillow numpy` and Node 22+. Screenshots, QA and PDF use Edge
or Chrome. Run browser and export jobs one at a time.

- `python` below means `python3` on macOS.
- Windows-only, because they drive PowerPoint through COM: the animated PPTX (entrance animations, clip
  autoplay, embedded fonts) and PowerPoint's own slide renders (`render_pptx.ps1`, `export.py --render`).
  On macOS the export still writes an editable PPTX, without animation, and you skip the PowerPoint
  render comparisons.

## 0. Where are we?

- Find the deck: a folder with `index.html` + `deck.json`. If the project's CLAUDE.md has an
  `html-presentation` section, it names the folder.
- **If a deck exists, check `DECK/review.json` first** (step 2), then do what was asked.
- No deck yet: the argument says `new …` or `from X.pptx`. If it's unclear which, or what the deck is about, ask.
  - The default folder is `deck/` in the current directory. Say where you put it.
  - Pass `--lang th` for Thai decks; it sets `<html lang>` and the review toolbar's labels.

## 1. Start

**From an existing PPTX or template:**

```
python <skill>/scripts/init_deck.py DECK --from SOURCE.pptx [--lang th] [--font "Family"]
node <skill>/scripts/shoot.mjs DECK --qa
node <skill>/scripts/shoot.mjs DECK SHOTS
powershell -File <skill>/scripts/render_pptx.ps1 -deck SOURCE.pptx -out SRC_RENDER     # Windows + PowerPoint only
python <skill>/scripts/compare.py SRC_RENDER SHOTS SIDE                                # Windows only; then look at SIDE/*.png
```

On macOS there is no PowerPoint render to compare against. Look at the SHOTS next to the source deck
opened in PowerPoint or Keynote, or ask the user to.

- The converter resolves master/layout text styles, table styles, theme fills, layout background
  pictures and bullets. Master artwork becomes a locked background layer.
- It keeps every shape name and id, so the export can replay edits onto the source's own XML (speaker notes,
  charts and layouts survive).
- Fix what doesn't match directly in `index.html`. Limits are in `references/export.md`.

**New deck:**

```
python <skill>/scripts/init_deck.py DECK --new --title "…" [--lang th] [--font "Family"]
```

This writes a 6-slide starter: title, section, three cards, text + picture, table + tip, summary. The
starter is a **vocabulary sample, not a template**. It shows how each element is written, and its
layouts and palette are placeholders. Replace all of it with a design made for this deck:

- Write slides only in the vocabulary of `references/format.md`: absolutely positioned `.sh` / `.tx` /
  `.pic` / `.tbl` with inline px styles. That is what the review toolbar, the QA check and the PPTX
  writer understand. Inside that vocabulary the design is yours to invent.
- **Brand first.** If the user, the project or another installed skill has a brand (colours, logos,
  background motifs, a .pptx template), build the look from it. Pull colours and logos from the
  source and put logos in `DECK/media/`. Never draw or invent a logo you don't have; use a text wordmark.
  Without a brand, choose a palette that suits the topic instead of reusing the starter's blue.
- **Design each slide around its message.** Pick the form that shows the idea: a diagram, a timeline,
  a split comparison, a big statement, a ripple, a menu, a chart, a table, a single number. Don't fall back
  to a row of equal cards. As a rule of thumb, no two slides in a row share a layout, and a deck uses
  card grids at most two or three times.
- One message per slide. Keep a small set of anchors consistent so the deck feels like one piece:
  for example the kicker and title position, margins, the logo spot and a footer motif. Everything
  else can change from slide to slide.
- Motion should explain something: a request travelling, a list being checked, a line being drawn,
  a ripple spreading. Vary it with the idea, and don't repeat the same effect on every slide. The
  `.fx` motion layer in `references/format.md` is for this; entrance motion stays with `deck.js`.
- Pictures and clips go in `DECK/media/`.
- Run `python <skill>/scripts/deck_tool.py renumber DECK` after adding, removing or reordering sections.

Both paths also create:

- The user's review launcher in the current directory: `review.cmd` on Windows, `review.command` on
  macOS (double-click in Finder; it is made executable).
- An `html-presentation` section in the project's CLAUDE.md, so later sessions know the loop without
  this skill.

Tell the user about both. Then screenshot every slide, look at them, and run `--qa`.

## 2. The review loop (start of every turn while the deck is in progress)

The user double-clicks `review.cmd` (Windows) or `review.command` (macOS), which opens a localhost server on port 8765 in the browser.
In the toolbar, **E** edits text in place, **C** drops a comment pin, and **H** hides pins.
Everything autosaves to `DECK/review.json`.

1. `python <skill>/scripts/apply_review.py DECK`, then add `--write`.
   - An edit is applied only if the box still holds its `before` text. Skipped edits are listed;
     handle them by hand.
2. Do each open comment in `index.html`, then set `"done": true` and a short `"reply"` on it, in the
   user's language. The user reads replies in the pin's pop-up. Never delete comments; that is the user's call.
3. Screenshot the slides you touched (`node <skill>/scripts/shoot.mjs DECK SHOTS 3,7`), look at them, and run `--qa`.
   Fix overflow above about 2 px.

The user can present from `DECK/index.html` at any time (over `file://`, so no toolbar shows):

- → / Space: next slide. ← / PgUp: back. Home / End: first / last.
- `f` (or `ด`) / Enter: toggle fullscreen.
- `#N` in the URL jumps to slide N.

Clips start and loop when their slide opens. Elements rise in reading order, and animation stays off in
screenshots and print.

## 3. Export (only when the user asks)

```
python <skill>/scripts/export.py DECK --pptx "OUT.pptx" --pdf "OUT.pdf" --render RENDER_DIR   # Windows
python <skill>/scripts/export.py DECK --pptx "OUT.pptx" --pdf "OUT.pdf"                         # macOS
```

- Name outputs after the deck title, next to the deck folder, unless the user says otherwise. If
  `~$OUT.pptx` exists the user has the file open; ask them to close it.
- Then check, and report what you actually saw:
  - Read the warnings the export prints (anything it could not express).
  - `python <skill>/scripts/check_anim.py OUT.pptx`: all effects should be `withEffect` and auto-start, with the
    longest reveal about 1.2 s or less. On macOS it reports no animation; that is expected.
  - Windows: `node <skill>/scripts/shoot.mjs DECK SHOTS`, then `python <skill>/scripts/compare.py SHOTS RENDER_DIR SIDE`
    and look at the SIDE images. Up to about 5/255 is text smoothing.
  - macOS: tell the user the PPTX has no animation, and that its fonts are not embedded.
  - If the pptx skill is installed: its `scripts/office/validate.py OUT.pptx` (add `--original DECK/.source/source.pptx` for converted decks).
- How the export works, what is HTML-only and the PowerPoint COM gotchas are in `references/export.md`.

## Rules

- `init_deck.py` refuses to overwrite an existing `index.html`. Never work around that, and never edit
  `DECK/.source/`: the baseline is what the export diffs against.
- Keep `data-id` / `data-src` / `data-layout` as they are. Don't invent ids. When you copy an element,
  drop its `data-id`.
- No per-element animation markup on `.sh` / `.pic` / `.tbl`. `deck.js` animates them by reading order;
  tune it there. Explanatory motion goes in a `.fx` layer (see `references/format.md`), which is HTML-only.
- Content rules (wording, terminology, house style) belong in the project's CLAUDE.md, not in this skill.
- Stop any server or browser you started yourself. The user's review window is theirs to close.
