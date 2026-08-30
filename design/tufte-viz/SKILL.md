---
name: tufte-viz
description: |
  Ideate and critique data visualizations using Edward Tufte's principles from "The Visual Display of Quantitative Information." Use this skill when:
  (1) Designing new data visualizations or charts
  (2) Critiquing or improving existing visualizations
  (3) Reviewing dashboards or reports for graphical integrity
  (4) Deciding between visualization approaches
  (5) Reducing chartjunk or improving data-ink ratio
  (6) Planning small multiples or high-density displays
  (7) Deciding whether a chart should describe the data or support inference from it
  Applies principles: data-ink ratio, chartjunk elimination, graphical integrity, lie factor, small multiples, and data density.
---

# Tufte Visualization Ideation

Apply Edward Tufte's principles to design clear, honest, high-density data visualizations.

## Workflow

### For new visualizations:

1. **Clarify the data story**
   - What comparisons matter?
   - What's the key insight to communicate?
   - Who's the audience?
   - **Descriptive or inferential?** Descriptive displays summarize the data in hand (what happened); inferential displays support prediction or a decision beyond the data (what it implies). Name which one before choosing a form — it decides what must be shown.
     - Descriptive → show the values themselves: tables, sparklines, small multiples, ordered bars. No trend lines, no extrapolation, no error bands implying a population.
     - Inferential → show the uncertainty with the estimate: confidence/prediction intervals, sample size, model fit vs. observed points, and the range over which the claim holds. An inferential chart that hides its uncertainty is a lie factor problem, not a style problem.
     - Mixed is fine, but mark the boundary visually — observed data and modeled/projected data must not share the same mark style.

2. **Select approach** using Tufte principles:
   - High comparison need → Small multiples
   - Dense data → Consider data tables, sparklines
   - Time-series → Line charts with minimal grid
   - Part-to-whole → Avoid pie charts; prefer bar/table

3. **Design with data-ink in mind**
   - Start minimal, add only what's necessary
   - Every element must earn its ink
   - Default to grayscale; use color purposefully

4. **Apply the eraser test before shipping**
   - For every element (label, tick, gridline, border, annotation): can it be erased without losing information that's not already conveyed elsewhere?
   - Watch for duplicate encodings: numeric labels next to a value already marked by a tick; legends duplicating direct labels; per-panel scale annotations duplicating a shared-scale caption.
   - If two elements compete for the same job, keep the visual one and drop the textual one (or vice versa) — not both.

5. **Apply the collision test before shipping**
   - For every text element in the plot (axis labels, point annotations, epoch labels, baseline labels, explanatory notes): mentally draw its bounding box. Does anything else — another text element, a data line, dense markers — live in or cross that box?
   - The eraser test catches *redundant* elements; the collision test catches *crowded* ones. Both must pass.
   - Standard fixes: move explanatory prose out of the plot into the figcaption; relocate band/epoch labels to a dedicated strip above the plot; push baseline/reference labels to the outside margin; give each in-plot annotation a leader line so the marker and the text occupy clearly separated space.
   - Watch especially: inverted axes (top of plot is now where extreme values cluster, where annotations also want to go); shared-scale small multiples (labels stacked near zero in every panel); dense scatter (text vanishes into the dot cloud unless explicitly cleared).

6. **Apply the Tufte test** (see references/tufte-principles.md)

### For critiquing visualizations:

1. **Check graphical integrity**
   - Calculate lie factor if proportions seem off
   - Verify baselines and scales
   - Look for 3D distortion

2. **Identify chartjunk**
   - Decorative elements
   - Heavy grids
   - Unnecessary 3D effects
   - Moiré patterns

3. **Check descriptive/inferential fit**
   - Does the chart claim more than the data supports (a trend line over three points, a projection with no interval)?
   - Or less than it should (a decision-support chart showing only point estimates)?
   - Flag any modeled or projected element drawn identically to observed data.

4. **Evaluate data-ink ratio**
   - What can be erased?
   - What's redundant?

5. **Suggest improvements** with specific before/after recommendations

## Key Principles Reference

- `references/tufte-principles.md` — core principles from *Visual Display of Quantitative Information*: lie factor, data-ink, chartjunk, small multiples, integrity.
- `references/analytical-design.md` — extensions from *Envisioning Information*, *Visual Explanations*, and *Beautiful Evidence*: the 6 principles of analytical design, sparklines, layering & separation, micro/macro, range-frames, causality, confections. Load when designing dashboards, dense displays, sparklines, or explanatory graphics.

**Quick checklist:**
- [ ] Lie Factor ≈ 1.0 (no visual distortion)
- [ ] Maximum data-ink ratio
- [ ] Zero chartjunk
- [ ] Clear labeling
- [ ] Answers "compared to what?"
- [ ] Descriptive vs. inferential intent is explicit; if inferential, uncertainty and observed-vs-modeled are visually distinct
- [ ] Shows causality or mechanism where relevant
- [ ] Multivariate (not over-reduced)
- [ ] Words, numbers, images integrated — not segregated
- [ ] Reveals multiple levels of detail (micro + macro)
- [ ] Layering: primary data dominates, secondary recedes
- [ ] Appropriate data density
