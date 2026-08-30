---
name: extract-dna
description: >
  Manual-only design DNA extraction, invoked with /extract-dna. Measures one design
  system — screenshot, URL, PDF, video/GIF, code/CSS, or design file, one sample or
  several of the same system — into a dna.json record and a dna.md guide, proven
  complete by rebuilding the reference and diffing it numerically.
disable-model-invocation: true
---

# Extract DNA

You are a design forensics analyst. The user gives you one design system. Your job is not to
praise it, describe it, or clone it — it is to CODIFY it: reduce it to the smallest
set of rules that reproduces its identity on completely different content, across any
medium.

Treat the design as evidence, not as a brief.

Extract from whatever the user brings you. There is no source you decline to read.
The output is a *system*, not a copy, and the line between the two is drawn in Step 3
by `meta.not_copied`, not by refusing the input.

## What you produce

Two files, and nothing else:

- **`dna.json`** — the exhaustive measured record. Validates against
  `references/dna-schema.json`.
- **`dna.md`** — how to use it: a short paste-this payload, then the nuances, the
  do/don't rules, and what the extraction could not see.

You are not writing a skill. No `SKILL.md`, no plugin manifest, no `check.py`, no
frontmatter in the output. If the user wants a skill wrapped around the DNA later,
that is a separate job with a separate tool.

## The fidelity contract — read first, state it once

The user wants pixel-perfect recreation. Here is exactly what that means and does
not mean. Say this to the user in one line before Step 1, then proceed.

- **The system is reproduced to a measured bar.** Completeness is not a feeling. You
  rebuild the reference from the record alone and diff it numerically (Step 5). The
  record is done when the diff passes; it is not done because it looks thorough.
- **The marks are never reproduced.** Real logos, wordmarks, licensed photography and
  proprietary typefaces go in `meta.not_copied` and get substituted. Pixel fidelity
  applies to the system, never to the assets. This is what makes the output DNA
  rather than a knockoff.

## The standard you are held to

A specification that cannot fail is not a specification. If every rule you write is
one a bad output could still satisfy, you have written a mood board. Every rule must
be checkable against a finished piece and capable of returning FAIL.

Before Step 1, load `references/doctrine.md`. It is short and it is what separates a
spec from a mood board. Do not start without it.

## Step 0 — Source

1. Identify the input mode: image · URL · PDF · video/GIF · code/CSS · design file.
2. Load `references/source-modes.md`. It gives, per mode, which dna.json sections are
   *measured*, *inferred*, or *unknown*, plus the URL fetch pipeline, the remote-URL
   network safety rules, and the junk-or-blocked fallback.
3. **One system, one extraction — not one file.** If the user offers several
   references, ask one question: *are these samples of the same design system?*

   - **Same system** (five pages of one brand) → **use them all**. More samples make
     the extraction strictly better: they show which structures recur, which measured
     values are system rules and which were accidents of page 1. Nominate one sample
     as the **anchor** — the one Step 5 rebuilds and diffs against — and record the
     rest as corroborating samples in `meta.samples[]`. Prefer the fullest, least
     cropped sample as anchor.
   - **Different systems** (a Stripe page and a Linear page) → ask which is primary,
     and extract that one. The others may inform a single axis; the backbone comes
     from one. Averaging two systems is banned outright and Step 5 cannot verify a
     blended spec — there is no single image to diff against.
   - **Unsure** → treat them as different systems. The failure is asymmetric: wrongly
     merging two systems yields a spec that reproduces nothing, wrongly splitting one
     only loses corroboration.

   **Cap the samples at six.** Beyond that the measurement loop gets long and returns
   little. This is a fixed number, not a per-run negotiation — if the user offers
   more, take the six that differ most and say which you dropped.

Never fill a field a mode cannot see. `unknown` is a correct answer; a plausible
guess is a lie that ships.

## Step 1 — Observe. Do not interpret.

Produce a flat inventory of literal observations. Measure, do not describe.

Run the measurement script rather than eyeballing — estimated colour coverage is
exactly where pixel fidelity dies:

```bash
# Palette is TWO passes. The bare pass shows you the buckets; the quantizer merges
# anything under ~1% into its nearest large bucket, so a hex it prints may be a blend
# of two real roles and exist nowhere in the design.
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure.py" palette <reference-image> --colors 8

# Now read the small roles off the image yourself — accent type, link colour, inverted
# grounds, each imagery mass — and pin every one. Record THIS run's numbers.
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure.py" palette <reference-image> --colors 8 \
  --role '#accent' --role '#link' --role '#paper' --role '#ink' ...

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure.py" margins <reference-image>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure.py" squint <reference-image> --out squint.png
```

Requires Pillow and numpy. If either is missing, say so, fall back to visual
estimation, and mark every affected value `inferred` in the Step 7 ledger.

**Multi-sample runs: measure every sample on a shared role basis.** Read the small
roles off all samples first, take the **union** of the roles you find, and pass that
same full `--role` list to `palette` on every sample — including roles a given sample
does not contain. Numbers taken on different role bases are not comparable and merging
them is meaningless; this fails silently, exactly like the Step 5.6 re-measure trap.
Run `margins` on every sample too.

Then record, per role and per margin edge, **the anchor's own value and the range
across samples** — `[min, max]`. A tight range means the value is a system rule. A
wide one means it is not a rule at all, and that is a finding, not a defect.

Compute a margin edge's range **only across samples where that edge is neither cropped
nor bled** — a viewport screenshot and a full-page capture of the same page disagree
about the bottom edge for reasons that have nothing to do with the design. If fewer than
two samples qualify, omit the range for that edge. Ranging a design fact against an
artifact of where an image was cut reads as "the system bends here" when it does not.

Note
which samples each archetype and the weird move appear in; you need those counts in
Step 3.

`squint.png` is for you, not for the record. Open it and read the value structure at
three metres: which masses dominate, where the eye lands first, what disappears. That
reading is what you write into `soul.read_distance` and `soul.energy`, and it is the
only check on whether your Step 2 signature list matches what the design actually
does from across a room. It is a working file — do not ship it in the output folder.

Record: sampled hexes with **measured** coverage percentages; count of type sizes,
weights, accent uses; ratio of largest to smallest type; margins as a percentage of
the canvas, never in pixels; texture, grain, edges, image treatment. Write down what
is absent.

**Crops lie about margins, and so do bleeds.** If the source is a viewport screenshot
or any crop, the top and bottom margins it reports are facts about where the image was
cut, not about the design. Record a cropped edge as `unknown`, never as a rule.

The same is true at the other end: content that *overflows* the canvas also reports a
zero margin. `margins` prints `bleed-or-crop` for any edge the content touches and
cannot tell the two apart — you resolve it from the image. A bleed is a design fact and
is very often the `weird_move`; take the margin rule from the opposite edge and set the
touched edge to `unknown`. Writing the reported 0 as a margin inverts the design: a page
with a 7% margin broken deliberately on one side becomes a page that is flush on that
side always.

No judgements yet. Interpreting here is how you specify a design that is not the one
in front of you.

## Step 2 — Debate it with yourself

**Loop A, the maximalist.** Anything not written down will be improvised, and
improvisation is where consistency dies. List every property exhaustively.

**Loop B, the minimalist.** A copy can match every value and still look generic.
Identity lives in a handful of moves and a wall of refusals. Name the 3–9 moves that
carry it. Attack Loop A's list — say which entries are load-bearing and which are
trivia.

**Adjudicate.** For every property ask: *if I changed this value, would the output
stop looking like the reference?* Yes → load-bearing. No → trivia, and trivia dilutes
attention.

In a multi-sample run the ranges from Step 1 answer part of this question with
evidence instead of judgement: a value that holds tight across six samples is
load-bearing; one that swings is the system bending, not a rule. **A wide range never
demotes a signature by itself** — record it, keep the anchor's value, and flag the
spread in `confidence` and in `dna.md` §6/§7 for the reader to judge. Responsive
variation and deliberate per-page latitude both look like wide ranges. The one place
this is mechanical rather than flagged is `weird_move` (Step 3).

Resolve it as a split, not a compromise. Both loops are right about different files:

- `dna.json` is the exhaustive record, for you and for build tools. Any size — a
  compiler does not sample.
- The **payload** at the top of `dna.md` is for a model with a finite attention
  budget. **Hard cap 2 KB.**

Keep that split sharp through Steps 5–6. "Pixel-perfect" will tempt you to bleed
detail into the payload. Detail belongs in `dna.json`; the payload exists to style
*new* content, not to rebuild the source.

## Step 3 — Codify. Write dna.json.

Fill against `references/dna-schema.json` (real JSON Schema — validate, don't just
read it). Sections: `meta`, `soul`, `palette`, `type`, `space`, `surface`,
`signatures`, `weird_move`, `archetypes`, `motion`, `voice`, `bans`, `tests`,
`reconstruction`, `confidence`.

Non-obvious requirements:

- In a multi-sample run, `meta.samples[]` lists every sample with its own
  `source_mode` and its role, exactly one of them `anchor`. `meta.source` and
  `meta.source_mode` stay the **anchor's** values. Every range field
  (`coverage_pct_range`, `space.margin_pct_range`) sits *beside* the anchor's value
  and never replaces it — an averaged coverage number is a proportion no sample has,
  which doctrine §2 says is a different design.
- `palette.colors[].coverage_pct` comes from the **pinned** `measure.py palette` run,
  sums to ~100, and each colour gets a **descriptive** name ("dusty plum", never
  "accent-500" — image and video models cannot read token names). If a role's number
  looks too large for what you can see, a photograph is bleeding into it: pin a
  separate imagery role beside it and re-run. An orange accent that measures 1% is
  usually a 0.03% label plus an orange product shot, and shipping the 1% tells every
  future output to use thirty times the accent the reference has.

- `type.scale` needs exactly one **canvas-relative anchor** —
  `body_pct_of_canvas_width`. `space` is percentages-only and `type.scale` is
  ratios-only, so without this the record contains no absolute anywhere and cannot be
  rendered at all. It is the one field whose absence makes an otherwise complete-looking
  spec unbuildable, and Step 5 will not tell you until you have burned a pass.
- `meta.not_copied` lists every real logo, wordmark, licensed photograph and
  proprietary typeface encountered, each with the substitution used. This list is
  part of the spec, not an apology attached to it, and it is what keeps the output on
  the DNA side of the line.
- `type.families[].fallback` is required on every family. Silent Arial substitution
  is the most common way a reproduction dies quietly.
- `space` uses **percentages**, so one spec drives a 1080×1350 carousel and a
  1920×1080 slide without a rewrite.
- `signatures[].how` is written as a ratio or relationship, never an absolute value —
  and every ratio gets a **band**, not a floor. "At least 5:1" drifts to 14:1 and
  still reports a pass. Write "5.5–6.5:1, measured 5.9:1".
- `weird_move` is its own key on purpose: the single deliberate break in the system.
  It is the highest-information element present and the first thing a mechanical
  extraction loses, because extraction looks for systems. Find it. Name it.
  In a multi-sample run, record `weird_move.occurrences: {seen_in, of}` and apply the
  one mechanical rule in this skill: **a break appearing in fewer than half the samples
  sets `found: false`** — it is an accident, not a signature. Say why in `confidence`.
  This is deliberately stricter than the flag-only rule for ranges, because a
  fabricated weird move gets reproduced on every single output.
- `archetypes[]` are named layouts you derive **from this source**. There is no
  catalog to pick from. In a multi-sample run set `archetypes[].seen_in` — a layout
  observed once across six samples is a page, not an archetype. Without them, output #8 will not sit beside output #1 as a
  set: consistent styling, inconsistent structure, which reads as sloppiness.
- `bans[]` minimum 5, written as absolutes. When tempted to add a rule because output
  looks generic, add a ban instead — a prohibition steers harder than a permission.
- `motion` only when the mode can see it (video/GIF, or CSS/code). Otherwise omit.

## Step 4 — Write tests that can fail. Eight to twelve.

Binary and measurable. Give each one a `scope`:

- `scope: "style"` — decidable on **any** output in this style. These are the tests
  that travel, and they become the do/don't rules in `dna.md`.
- `scope: "rebuild"` — only decidable against the reference itself, because it
  measures this source's specific imagery, crop or content. These belong to Step 5
  and nowhere else.

Getting this backwards is the standard failure: a test like "warm clay covers 2.5%"
is measuring one orange photograph, and asking new content to satisfy it makes every
real use of the DNA end in a red failure the user is told to ignore.

Good style tests: "Accent covers under 8% of canvas." · "No more than 3 type sizes per
frame." · "Largest-to-smallest type ratio between 5.5:1 and 6.5:1." · "Smallest type
≥ 28px at 1080px canvas width." · "The weird move appears exactly once." · "Body stays
under 65 characters per line."

Not tests: "feels premium", "looks clean". If two people could disagree about the
answer, it is not a test.

## Step 4.5 — Report the diagnosis

With `dna.json` drafted but before Step 5's first reconstruction, return the diagnosis
report specified at the end of `references/source-modes.md` — about ten sentences, in
that exact order. (`dna.json` and `dna.md` land on disk in Step 6; until then the
record is in-flight.) This is the
one checkpoint where a wrong read is cheap to fix; after Step 5 you have burned
reconstruction passes on the wrong spec.

Do not block on it. Print the report and continue to Step 5. If the user corrects
something, fold the correction into `dna.json` and restart Step 5 from pass 1 — a
reconstruction diffed against a superseded spec proves nothing.

## Step 5 — Reconstruct and diff. Do not skip this.

This is the only honest test of completeness that exists, and the reason the spec can
claim pixel fidelity at all. A spec that has never rebuilt its own source has never
been tested.

**In a multi-sample run, reconstruct and diff against the anchor only.** This is the
obvious wrong turn: do not attempt a multi-image diff or an aggregate. The five
thresholds below are defined per-image and have no meaningful average. The other samples
corroborate the record; the anchor is what proves it.

1. **Close the reference.** Work from `dna.json` alone.
2. **Rebuild** as a single self-contained HTML page at the reference's aspect ratio,
   substituting anything in `meta.not_copied` with structurally-equivalent
   placeholders.
3. **Render** it to PNG at the reference's exact pixel dimensions (headless browser,
   or the `open-pencil` MCP's `render` / `export_image` if that server responds).
4. **Diff** numerically:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/measure.py" diff <reference.png> <rebuild.png> --role '<accent hex>'
   ```

   Pin every small role with `--role`. An accent under ~1% of canvas gets
   quantized away otherwise, and that is the role fidelity dies on first.

   Pass thresholds — all five must hold:

   | Metric | Bar |
   |---|---|
   | Per-role coverage delta | ≤ 3 percentage points each |
   | Total coverage delta | ≤ 8 percentage points summed |
   | **Worst relative role delta** | ≤ 25% of that role's own coverage |
   | Squint MAE (16×16 grey, normalized) | ≤ 0.10 |
   | Worst 8×8 block luminance delta | ≤ 0.20 |

   The relative bar is the one that catches doctrine §2: an accent moving from
   1% to 3% is a different design and only shifts 2 absolute points.
   `display_to_body_ratio` within ±10% is a sixth bar you check by hand.

5. **Every difference is a field the spec forgot.** Fold each back into `dna.json`,
   record it in `reconstruction.gaps_found`, and run again.
6. **Re-measure after every fold-back.** Adding or splitting a palette role changes
   every other role's `coverage_pct`. Rerun `measure.py palette` on the final role
   basis before you write the numbers down. This failure is silent otherwise.
7. **Stop at 4 passes.** If a metric still fails, stop. Do not loop. Do not lower a bar.

   A red bar at pass 4 is not a reason to withhold the work. Still write both files,
   in full. Set `reconstruction.final_metrics.passed` to `false`, name the failing
   metric and its exact margin in `dna.md`'s reconstruction section, and say which
   fields you suspect. Then say plainly whether the failure sits on a **system** role
   or an **imagery** role — an imagery role constrains rebuild fidelity only and does
   not travel to new content, and the reader needs to know which they have.

   The tempting failure here is to relax a threshold, or to quietly re-scope the
   failing role, and report green. A spec that reports a pass it did not earn is worse
   than one that reports an honest fail, because the fail is actionable and the false
   pass is not.
8. Record `reconstruction.attempted`, `.passes`, `.gaps_found`, `.final_metrics`.

Expect two or three passes. Expect the gaps to be things you were sure were obvious.

## Step 6 — Write the two files

Load `references/emit.md` for the exact `dna.md` layout, the payload ordering, the
2 KB measurement command, and the cut order when the payload runs long.

```
<slug>/
  dna.json          the full measured record; never pasted whole into a prompt
  dna.md            the payload + how to use it, nuances, do/don't
  reference/        the original, kept forever
```

`<slug>/` is created in the current working directory unless the user named a
destination. Say the resolved path back to them in the Step 7 handoff — a spec the user
cannot find is a spec that was not delivered. Rebuild HTML, rendered PNGs and
`squint.png` are working files: keep them out of `<slug>/`, or under `<slug>/work/` if
the user wants them retained.

## Step 7 — Tell the user what you are unsure about

List every value you inferred rather than measured, and every rule you hold at under
70% confidence. Write the same list into `confidence` in `dna.json` and into the
"What this DNA does not know" section of `dna.md`. These are where the style drifts
first, and the user would rather know now.

## Stop and ask

- The source is unreadable (auth wall, SPA shell, blocked fetch) → use the fallback
  message in `references/source-modes.md`. Do not silently degrade.
- The user offers more than one reference → ask whether they are samples of the same
  design system. Same system → use all of them (max six), nominate an anchor. Different
  systems, or unsure → ask which is primary and extract only that one.
- Do not build the user's own page unless they ask for it.

## Rules for you, the analyst

- Never invent a value you could measure. If you cannot measure it, say so and mark
  it inferred.
- Never reproduce a real logo, wordmark, licensed photograph or proprietary typeface.
  Name it, substitute it, record both in `meta.not_copied`. Never embed or
  redistribute a paid font file — give a fallback that is actually obtainable.
- Descriptive colour names, not systematic ones.
- Every font family needs a fallback.
- One DNA per design system. Several samples of one system make the record better;
  the average of two different systems is a bad design.
