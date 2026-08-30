---
name: chart-viz
description: Manual-only chart decision framework, invoked with /chart-viz. Resolves chart type, color, decluttering, emphasis, and sorting against the question, data shape, medium, and audience rather than applying a fixed checklist.
disable-model-invocation: true
---

# Data Visualization

## Core stance

There are almost no universal rules in charting — only defaults that hold under some conditions and reverse under others. A technique that sharpens one chart ruins another. So the job is never "apply the checklist." The job is: identify the context, then pick the technique whose trade-offs fit that context.

Before touching any chart, establish four things. Every downstream decision depends on them.

1. **The question.** What exactly should the reader be able to answer at a glance? "Top 3 per series," "is the trend up or down," "which segment dominates," "did we hit budget." A chart optimized for one question is usually worse for another. If the question is undefined, the design has no target and cannot be evaluated.
2. **The data shape.** How many categories, series, data points? Part-to-whole, ranking, comparison across groups, distribution, correlation, or change over time? The structure of the data constrains which encodings even work.
3. **The medium.** Static (print, PDF, slide, image, social) or interactive (dashboard, app, notebook)? Interaction (sort, filter, hover, drill) is a real design element in one and unavailable in the other. Never propose interactive fixes for static output.
4. **The audience and use.** One-time communication of a fixed message, or repeated exploration/monitoring? Expert or general? Known viewing conditions (grayscale print, projector, colorblind users)? Communication charts can bake in a single answer; exploratory charts must preserve signals the reader might look for later.

State assumptions about these inline when the user hasn't specified them, and let the choices follow from them. When two contexts conflict (e.g., "top 3 per series" AND "compare totals across series"), name the conflict — a single chart often can't serve both, and the honest answer is to pick one or use two views.

## How to use the technique sections

Each section below gives a default, the conditions under which it holds, and the conditions under which it reverses. Read them as "if / then," never as "always." When the user's context isn't stated, infer it from the question and data, or ask one targeted question if the right choice genuinely hinges on it.

Never carry a verdict over from the example below, from a chart redesigned earlier in the conversation, or from a familiar before/after genre — re-derive from *this* chart's four context facts. If a redesign is converging on a move list you recognize, that is a reason to re-check the derivation, not confirmation that it's right.

---

## Chart type selection

Match the chart to the *question about the data*, not to habit or to what the tool defaulted to.

- **Part-to-whole / composition, and the total matters** → stacked bar, or (for a single whole) a proportion bar. Stacking exists specifically to show totals and how a whole divides. Keep it when the reader cares about the sum.
- **Ranking components *within* a group** → split into separate bars per group, or grouped bars. Stacking is bad for this: only the bottom segment sits on a common baseline, so the other segments are nearly impossible to compare across categories. This is the classic reason to break a stacked bar apart.
- **Comparing the same components across many categories** → grouped bars (no totals needed) or small multiples.
- **Change over time** → line chart, usually. Bars for time work only for few periods or when discrete counts matter.
- **Distribution** → histogram, box, or strip/beeswarm.
- **Correlation** → scatter.

**The recurring tension across these options is splitting.** Any move from one chart to several — a stacked bar into per-series panels, one multi-line chart into small multiples per region, a scatter into a facet grid — buys clarity *inside* each panel at the cost of the shared scale and shared totals that let panels be compared *against each other*. Split when the reader's question lives inside a panel; keep one chart when it lives across them. Don't split reflexively because the original looked busy.

## Color

- **Default: use colorblind-safe palettes.** Software defaults (red/green pairings especially) fail for a meaningful fraction of viewers. Test palettes with a simulator; favor combinations distinguishable across common color-vision deficiencies (blue/orange, and gray for de-emphasis, are safe workhorses).
- **Never let color be the *only* channel carrying meaning.** Pair it with position, ordering, direct labels, or shape. This protects against grayscale printing, full color blindness, and projector washout. A chart whose message survives being printed in black and white is robust; one that doesn't is fragile.
- **Check luminance contrast, not just hue difference.** Two hues that differ on screen can collapse to the same gray.
- **Use color quantity deliberately.** More than ~6–7 distinct hues stops being decodable; switch to grouping, faceting, or direct labeling instead.

## Decluttering: gridlines, axes, labels

This is the most context-dependent area — treat any "always remove X" advice with suspicion.

**Default framing:** remove gridlines and axis lines *only to the extent they carry no information the bar lengths or data labels already convey.* Ink that duplicates information is clutter; ink that provides a reference is not.

**Stripping the axis/gridlines and adding direct data labels works well when:**
- Few data points (roughly a handful to a dozen), so labels don't collide.
- The goal is a single glance-level takeaway rather than analysis.
- Exact values matter more than proportional feel — a label gives the precise number a gridline can't.

**It breaks down when:**
- Many bars or points: direct labels clutter and scan *worse* than one shared axis.
- Cross-chart or cross-series comparison is needed: a shared scale lets the eye compare bar lengths directly; without it the reader must read numbers and compute differences mentally.
- Proportional context matters: a label says "8" but not intuitively whether that's near the max or triple the min. Bar length carries that only if the reader trusts the scale — and removing the axis removes the means to verify it.
- Exploratory or analytical use: dropping the scale trades rigor for cleanliness, a poor trade when magnitude judgments drive decisions.

**Compounding risk:** splitting a chart into small multiples (see chart selection) *removes the shared axis that would let those panels be compared.* So "split into panels" and "remove the axis" reinforce each other's downside. If comparison across the panels matters, don't do both — keep a shared axis, or keep a single chart.

Rule of thumb, not law: on a small single-message static chart, dropping axis + gridlines and labeling directly is usually right. On anything with many series, many categories, or a need for precise cross-comparison, keep at least a light axis or faint gridlines as a shared reference.

## Emphasis (directing attention)

- **Highlight the answer, mute the rest.** Rendering the marks that answer the question — the one region that missed target, the current quarter, the series under discussion — in full saturation and everything else in a light tint is preattentive emphasis, one of the strongest and cheapest techniques available. The eye finds the answer before conscious reading.
- **Conditions:** best for communication where the message is fixed. It *bakes in one specific answer*, so it fails a reader who arrives with a different question, and it goes stale on any view whose underlying data refreshes — avoid it for exploratory and monitoring views.
- **Payoff scales with clutter:** with a handful of marks the reader finds the answer anyway; across dozens, muting the non-answers is what makes the chart readable at all.
- **Robustness:** intensity emphasis weakens in grayscale unless the light/dark gap is large; make the contrast generous if grayscale is possible.

## Legends vs direct labeling

- **Prefer direct labeling** — series name at the end of its line/bar, or beside the data — over a separate legend. It removes the eye-movement and short-term-memory cost of matching swatches to a key.
- **Use a legend when** direct labels would overcrowd (many overlapping series, dense small multiples) or when a single legend cleanly serves several panels at once.

## Orientation

- **Horizontal bars** are a good default for ranking (natural top-to-bottom reading) and for long category labels (they fit without rotation). Horizontal orientation also pairs naturally with sorting.
- **Vertical bars / lines** are expected for time series (time reads left-to-right) and where the audience is habituated to a vertical convention.
- Orientation should follow the data's structure and label lengths, not a blanket preference either way.

## Sorting and interaction

- **Sort deliberately.** In static output, sort order is a fixed design decision — order by the dimension the reader most needs (magnitude for ranking questions, chronology for time, a fixed logical order for reference tables). Don't leave it alphabetical or source-order by accident.
- **Interactive sort/filter is a real tool — but only where the medium supports it.** Dashboards and apps can let the user re-rank on demand, which elegantly serves multiple questions from one view. This option simply does not exist for print, PDF, slides, or images; don't propose it there.

---

## Worked example: one chart, four contexts

This example exists to show how far conclusions travel when a single fact changes. It is deliberately not a recipe — the same input resolves four different ways below, and several of the branches contradict each other. Read it for the reasoning shape, not the moves.

**The input, held constant throughout:** a stacked bar, 6 categories × 3 series, default software colors.

**Base context** — Question: which category has the largest total? Data: small, part-to-whole where the sum is the point. Medium: static slide. Audience: one-time fixed message.
→ Keep the stack; the total *is* the answer. Sort categories by total. Swap defaults for a colorblind-safe palette. Drop gridlines and axis and label each bar's total directly — few bars, one message, exact values useful. Full saturation on the winning bar, light tint on the rest.

**Flip only the question** → "how do the three series rank *within* each category?"
→ Stacking now defeats the question, since only the bottom segment sits on a common baseline → grouped bars or per-series panels. Sorting by total stops helping; sort inside each panel by value. The single highlighted bar stops meaning anything. Same data, same medium, same audience — and the chart type reverses anyway.

**Flip the medium and the use together** → same question, but a dashboard people check daily. These two facts co-vary in practice, so track which one drives which conclusion.
→ Because the data *refreshes*: don't bake in emphasis — the winning category changes, so a saturated highlight encodes yesterday's answer — and restore the axis and light gridlines the base dropped, since a stable shared scale beats direct labels that redraw on every update. Because the medium is *interactive*: sort and filter become available at all, and they serve the questions the base chart had to exclude.

**Flip only the data size** → same question, same static slide, but 40 categories.
→ Direct labels now collide, so the base's declutter move reverses: bring back the axis and faint gridlines, drop the labels. Emphasis moves the *other* way — muting 39 non-answers matters more at 40 bars than at 6. And 40 stacked bars barely read as parts at all; consider top-N with an "other" row, or a dot plot of totals if the breakdown has stopped earning its space.

**What to notice:** decluttering was right in the base and wrong in two branches. Emphasis was right in the base, wrong on the dashboard, and *more* important at 40 categories. Two decisions that look alike flip in opposite directions on different facts. There is no column here to copy — every verdict traces to exactly one named condition, even in the branch where two facts moved at once, and naming that condition is the actual deliverable.

Present redesigns the same way: state the choice, name the condition it depends on, and say what you would do instead if that condition were different.

## When critiquing an existing chart

Diagnose against the four context dimensions before prescribing. Ask (or infer): what question is this meant to answer, and does the current design let a reader answer it quickly? Then attribute each problem to a specific mismatch (wrong chart for the question, color that fails colorblind viewers, clutter that adds no reference, missing emphasis, comparison defeated by split axes) and pair each fix with the condition that makes it the right fix. Avoid delivering a generic "remove gridlines, add labels, recolor" checklist — that's the exact template-thinking this skill exists to replace.

## Handing off once the encoding is resolved

This skill decides *which* chart and *what it emphasizes*. It has no ink-level cleanup pass and will not make the result look finished. Once the four context facts have produced an encoding, hand off:

- **`tufte-viz`** — run its eraser and collision tests *inside* the encoding chosen here, to strip duplicate ink and catch text that overlaps data.
- **`tufte-clarity`** — for the slide, page, or dashboard *around* the chart. Not for the chart.

**Run in that order; it does not commute.** `tufte-viz` optimizes a chart against its own checklist, not against a question. Applied first, it splits a stacked bar into small multiples that read beautifully and no longer show the totals the reader came for.

Its defaults will also try to reverse decisions made here on purpose. Accept a cleanup only when it leaves the answer to the stated question unchanged; reject it when it undoes something traceable to a named context fact. Recurring cases:

- **Grayscale-by-default** reverses emphasis that a fixed-message static chart earned, and collapses series that need hue separation to stay countable.
- **The eraser test on axes** reverses a shared scale that a refreshing dashboard or a cross-panel comparison depends on.
- **Range-frames** are a genuine win on static data, and wrong on a monitoring view — the frame's endpoints move on every refresh, which is the instability the axis was kept to prevent.

Cleanup that changes what the chart answers is not cleanup. Neither sibling checks color-vision safety; that stays this skill's job.
