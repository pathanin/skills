---
name: tufte-clarity
description: |
  Apply Tufte's information design principles to UI, web, and presentation design. Use this skill when:
  (1) Reviewing or designing UI layouts, components, or screens
  (2) Designing or critiquing web pages, landing pages, or marketing sites
  (3) Critiquing presentation slides or decks
  (4) Evaluating navigation, information architecture, or page hierarchy
  (5) Reducing decorative excess or chrome in any visual design
  (6) Choosing between layout or visual structure approaches
  Applies signal-to-chrome ratio, representational honesty, parallel structure, visual hierarchy, multi-scale legibility, and contextual co-location — Tufte's data-viz principles generalized to UI, web, and presentation design.
---

# Tufte Clarity: Information Design Beyond Data

Tufte's principles are fundamentally about honest, efficient communication of complex information. Data is just one type of content. These principles apply wherever something must be understood.

## Core Translation

| Data-Viz Concept | General Design Equivalent |
|---|---|
| Data-ink ratio | Signal-to-chrome ratio |
| Chartjunk | Decorative excess |
| Lie Factor / Graphical Integrity | Representational honesty |
| Small multiples | Parallel structure |
| Layering & separation | Visual hierarchy |
| Micro/macro | Multi-scale legibility |
| Eraser test | Necessity test |
| Comparison first | Relationship-first framing |
| Words + numbers + images integrated | Contextual co-location |
| Data density | Content density |
| Causality | Mechanism visibility |

---

## Workflow

### For UI / Interface Design

1. **Establish the primary action**
   - What does the user need to do or decide on this surface?
   - Does visual weight match action importance? Primary button must dominate secondary. (Representational honesty)
   - If a "Cancel" and "Delete Account" button look identical, that's a lie factor.

2. **Apply the necessity test to every element**
   - For each border, shadow, gradient, icon, divider, label: can it be removed without losing meaning or affordance?
   - Borders earn their ink only when proximity and background don't already separate regions.
   - Shadows and gradients earn their place only when depth/elevation carries functional meaning.

3. **Apply parallel structure to repeated content**
   - Settings pages, feature comparisons, pricing tables, list rows → same structure, varying content.
   - Identical visual encoding enables fast scanning. Structural asymmetry implies importance asymmetry — use intentionally.

4. **Co-locate labels with content**
   - Form labels belong adjacent to inputs, not in floating legends or placeholder text.
   - Error messages at the point of error, not at the top of a form.
   - Inline context beats tooltips; tooltips beat help panels; help panels beat FAQs.

5. **Apply the squint test**
   - Squint at the screen. Primary content should remain prominent; chrome should fade; decoration should disappear.
   - Anything that survives the squint that isn't primary content is over-weighted.

6. **Test multi-scale legibility**
   - **Glance (1 second):** primary action or claim is locatable
   - **Scan (5 seconds):** structure and sections are mappable
   - **Read (full attention):** detail is there when needed

---

### For Presentation / Slide Design

1. **One claim per frame**
   - Each slide answers a single question or makes a single assertion.
   - Multiple competing claims → split the slide, or use parallel structure (small multiples).

2. **Integrate words and images — don't segregate**
   - Captions and annotations belong on the same slide as the visual they describe.
   - Diagram on slide 4, explanation on slide 5 = segregated. Annotated diagram = integrated.
   - Bullets + separate visual = separated evidence. Labeled visual = integrated evidence.

3. **Parallel structure for comparisons**
   - Comparing two options? Identical layout for each — same structure, same visual weight.
   - Asymmetric layouts assert asymmetric importance. Use only when true.

4. **Eliminate the duck**
   - Background images, clip art, decorative transitions, brand treatments that draw attention to the design instead of the content.
   - When a viewer's first reaction is "nice template," the design has competed with — and may have won over — the content.

5. **Show the mechanism, not just the conclusion**
   - "We grew 40%" is a conclusion. The progression that produced it is the mechanism. Show both.
   - If causality matters to the argument, visualize the path from cause to effect.

---

### For Web / Marketing Design

1. **Visual hierarchy must map to content hierarchy**
   - The most prominent element on a page should carry the most important message.
   - A decorative hero image dominating the viewport at the expense of the headline is a lie factor.
   - Type size, weight, and color must track conceptual importance — not be applied decoratively.

2. **Hero sections and the duck**
   - A hero earns its size only when the visual directly reinforces the core message.
   - Stock photography, abstract backgrounds, and brand imagery that fill space without advancing the argument are ducks.
   - Test: cover the hero image. Does the page's message change? If not, the image is decorative excess.

3. **Co-locate CTAs with motivating content**
   - A call-to-action belongs adjacent to the content that motivates clicking it.
   - A "Sign up" CTA before any value proposition is a relationship-first failure — it asks the user to act without evidence.

4. **Navigation chrome should recede**
   - Sticky headers, mega-menus, and sidebars are structural chrome — they must not compete visually with page content.
   - A header that dominates the viewport while scrolling fails the squint test.

5. **Animations and transitions must earn their motion**
   - Motion that conveys state change, reveals structure, or guides attention earns its place.
   - Scroll animations, parallax effects, and entrance animations that exist for visual sophistication are chartjunk in motion.

6. **Typography hierarchy must be functional**
   - Headline > subheadline > body > label — font size and weight must follow this strictly.
   - Decorative display fonts applied at body scale break reading hierarchy.
   - Line length: 60–75 characters. Wider columns are chrome.

7. **Responsive density**
   - Desktop allows more parallel content — don't waste that density with padded single-column layouts.
   - Mobile requires vertical stacking — hierarchy must survive reflow without information loss.
   - The multi-scale test applies across all breakpoints.

---

### For Information Architecture / Navigation

1. **Relationship-first framing**
   - What is the most important relational question users arrive with?
   - Pricing page: "Which plan is right for me?" → surfaces comparison
   - Settings page: "What's currently on vs. off?" → surfaces current state
   - Error state: "What went wrong and how do I fix it?" → surfaces cause + action
   - Surface the answer to that question; don't make users excavate it.

2. **Navigation organized by user questions, not org structure**
   - Navigation built around how the organization works hides what users need.
   - The user's question is the data; the navigation must answer it.

3. **Reduce chrome in the hierarchy itself**
   - More categories ≠ more clarity. Unnecessary categories are structural chartjunk.
   - Every navigation item and section header must earn its presence.

4. **Prominence reflects usage, not organizational priority**
   - Most-visited content should be most visually accessible.
   - Giving visual prominence to organizational priorities at the expense of user needs is a lie factor.

---

## Universal Tests

### Necessity Test (Eraser Test generalized)
For every visual element — border, shadow, icon, label, section, heading, divider, color, animation:
> Can this be removed without losing meaning, function, or orientation?

If yes: remove it. Watch for **duplicate encoding**: a label that restates what an icon already conveys; a border that restates what whitespace already separates; a heading that restates what the section's opening line announces. When two elements do the same job, keep one.

### Squint Test (Layering check)
Squint at the design:
- Primary content remains prominent → good
- Structural chrome fades → good
- Decorative elements disappear → good
- Anything non-primary that survives the squint is over-weighted

### Representational Honesty Test
Does visual weight match actual importance?
- Primary action > secondary > tertiary — size, color, and placement must reflect this ordering
- If two actions look identical, the design claims they're equally important. Is that true?

### Multi-Scale Test
- 1-second glance: primary purpose of this surface is understood
- 5-second scan: structure is mappable
- Full read: detail is available for those who need it

### Collision Test
For every text element, draw its mental bounding box. Does anything else — another label, an icon, a decorative element — compete for the same space or role? If so, relocate or remove one.

---

## Quick Checklist

- [ ] Every visual element passes the necessity test
- [ ] Visual weight matches content importance (no lie factor)
- [ ] Parallel structure applied wherever comparison is needed
- [ ] Labels and context co-located with the content they describe
- [ ] Squint test: primary content dominates; chrome recedes
- [ ] Design rewards glancing, scanning, and careful reading
- [ ] Mechanism/causality shown where it matters, not just conclusion
- [ ] No decorative excess (shadows, gradients, borders without function)
- [ ] Comparisons surfaced, not buried
- [ ] Comparisons and CTAs placed adjacent to their motivating content

---

## References

- `references/clarity-principles.md` — full generalized principle set with examples and anti-patterns for each: signal-to-chrome, representational honesty, parallel structure, visual hierarchy, multi-scale legibility, contextual co-location, decorative excess, content density, relationship-first framing, mechanism visibility.
- See sibling skill `tufte-viz` for the data-visualization-specific application of these principles.
