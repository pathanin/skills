# Doctrine — what actually carries a design's identity

Load this before Step 1. Getting it wrong is the standard failure, and it is not a
failure of effort — a thorough extraction that misses these produces a long document
that reproduces nothing.

## 0. One system, not one file

Averaging two *different* designs destroys both — `weird_move` has no mean, and the same
three hexes at 60/30/10 and 90/8/2 are unrelated designs (§2, §3). That ban stands.

Several samples of the *same* system are the opposite case: they are more evidence about
one design, and they are what tells a system rule apart from an accident of page 1.
Measure them all on a shared role basis, keep the anchor's values, and record the spread
beside them.

## 1. Relationships, not values

"The headline is 96px" is nearly worthless. "The headline is 8× the body, never under
6×" is the identity. Style lives in the ratios between elements. A list of
measurements is exactly that information thrown away.

Every entry in `signatures[]` must be written as a ratio or a relationship. If you
catch yourself writing an absolute number outside `palette` and `meta`, ask what it
is a ratio *of*.

## 2. Proportions of colour, not just colour

The same three hex codes at 60/30/10 and at 90/8/2 are two unrelated designs. Always
record coverage. Measure it with `scripts/measure.py palette` — do not estimate it by
eye, because this is the single field where pixel fidelity most often dies.

## 3. One break in the system

Almost every design worth copying has exactly one deliberate exception: type crossing
an image, a rule overshooting its margin, a numeral clipped by the canvas edge.

It is the highest-information element present and the first thing a mechanical
extraction loses, because extraction looks for systems and this is a break from the
system. Find it. Name it. It gets its own top-level key, `weird_move`, so it cannot
be averaged into the rest.

If you genuinely cannot find one, say so explicitly in Step 7 rather than inventing
one. A fabricated weird move is worse than none — it will be reproduced every time.

With several samples of one system, a break seen once is an accident, not a signature.
Count it: appearing in fewer than half the samples sets `weird_move.found: false`. This
is the one place a multi-sample count decides a field mechanically, because the cost of
a false positive here is that every output reproduces someone's mistake.

## 4. Refusals, not just permissions

Listing six colours tells a model it may use six. If the reference uses one accent on
3% of the canvas, the design's real content is a refusal. Write the refusals down.

One ban rules out an entire space in a single line. A permission has to be re-earned
on every output.

## 5. Absence is design

No shadows. No icons. No curves. Nothing centred. Record what is missing with the
same care as what is present. The Step 1 inventory is incomplete until it has an
explicit absent-list.

## 6. Structure, not only styling

If a style has no named layouts, output #8 will not sit beside output #1 as a set.
You get consistent styling and inconsistent structure, which reads as sloppiness.

Derive `archetypes[]` from this source. Name them for what they do in a sequence, and
give each one a content budget — how much text and how many elements it can hold
before it stops being that archetype.

## The adjudication question

For every property you are considering recording, ask exactly this:

> If I changed this value, would the output stop looking like the reference?

Yes → load-bearing, it goes in. No → trivia, and trivia dilutes attention.

Run this honestly. Most extractions fail not by missing things but by recording
everything at equal weight, which is the same as recording nothing.
