# Mobile Patterns — Platform Mechanics

Load when implementing, not when critiquing. `SKILL.md` decides *what* to do; this file covers *how*, plus the numbers.

---

## Overlay contrast (D1)

Ranked by robustness, not by prettiness:

1. **Filled container behind the control** — a circular or rounded-rect neutral surface (not the brand color) with the glyph at full opacity on top. Survives every background; costs the most visual weight. Material's original imagery spec put dark scrims at 20–40% opacity and light ones at 40–60% — treat those as starting points from a deprecated spec, not as targets, and settle the value with the acceptance test below.
2. **Gradient scrim across the overlay band** — anchor its height to *the control it protects*, not to a percentage of the media. Material's original guidance was roughly 3× the bar height with the gradient midpoint offset toward the dark end, so the falloff has no visible edge. Cheaper visually than per-control containers, and it also protects status-bar glyphs.
3. **Glyph outline or drop shadow only** — a 1px contrasting stroke, or a soft shadow at low opacity and small radius. Lowest weight, least robust; adequate only when the media set is genuinely controlled (your own art direction, not user uploads). No platform guidance prescribes this; it is belt-and-braces on top of 1 or 2.

Combine 1 or 2 with 3 for user-generated media.

**The acceptance test replaces the magic number.** WCAG's failure technique F83 tests text against the lightest (or darkest) region of a *specific* image; 1.4.11 Non-text Contrast requires 3:1 for icon controls against adjacent colors — and explicitly lets you disregard adjacent colors that don't impede identifying the component. Neither covers an asset you haven't seen. Adapt F83 forward: require **4.5:1 for text and 3:1 for glyphs against the lightest region a permitted upload could contain**. Verify by rendering with the media replaced by `#FFFFFF`, then `#000000`, then a high-frequency noise or foliage image. Automate it if the media is user-supplied.

Any opacity figure without this test attached is the weakest thing in your spec — the published numbers are polarity-split and come from a 2014 document whose successor carries no replacement.

**Status bar:** put a protection behind the bar — scrim, gradient, or blurred view — and derive the light/dark style from *that protection*, since it is now what sits under the glyphs. Apple's guidance goes further: obscure content under the status bar outright, or hide the bar during full-screen media (as Photos does). Apple also warns that controls visible behind the bar invite taps that cannot land. On Android, targeting SDK 35+ enforces edge-to-edge and makes system bars transparent by default, so bar protection is required work, not polish.

---

## Collapsing header / content card (F1)

The pattern in three layers, bottom to top:

1. **Media layer** — pinned, full-bleed, extends under the status bar. Optionally parallaxes at ~0.5× scroll rate — that is Material's library default (`DEFAULT_PARALLAX_MULTIPLIER = 0.5f` in `CollapsingToolbarLayout`), so it is a real convention rather than a taste call — or scales up on overscroll-down (rubber-band zoom).
2. **Content card** — starts at an offset that leaves a meaningful portion of the media visible (~55–70% of media height works in practice; this is a craft default, not a platform spec — tune it to your media aspect ratio), has a top corner radius (16–24) and a subtle upward shadow, and scrolls at 1× over the media.
3. **Nav bar** — transparent at rest with only the overlay controls (D1 applies). As the title in the content card crosses the nav bar's bottom edge, cross-fade the nav background in and the title up into it.

Implementation notes:

- **Drive the transition from scroll offset, not from an intersection callback fired once.** You need a continuous 0→1 progress value to interpolate opacity; a boolean toggle produces a visible snap.
- **Cross-fade over a range**, not at a single threshold — a hard flip at one scroll offset reads as a glitch and flickers when the user rests mid-scroll. The principle is specified (Material exposes `TITLE_COLLAPSE_MODE_SCALE`/`FADE` with a 600ms default scrim animation), but Material expresses the range in *time*; expressing it as scroll distance instead (~24pt either side of the crossing point) is an equivalent craft choice, not a spec value.
- **The promoted title must truncate to one line.** A two-line nav title at large font scales pushes content down and breaks the layout that the collapse was meant to stabilize.
- **Keep the promoted title's text identical to the card title.** A shortened variant makes the promotion read as a different label.
- Native equivalents: `CollapsingToolbarLayout` with `app:layout_scrollFlags="scroll|exitUntilCollapsed|snap"` (Android), `UINavigationBar.prefersLargeTitles` or a custom `scrollViewDidScroll` interpolation (iOS), `Animated.ScrollView` + `interpolate` (React Native), `position: sticky` + an `IntersectionObserver`-derived progress or scroll listener (web views).
- **Scope note:** the *title-promotion* half is platform behavior on both sides. The *card-over-media* composition is an app-level pattern (Airbnb/Apple Music style), not a platform spec — it carries no built-in affordances you can rely on.

---

## Sticky bottom action bar (F2)

- **Safe area is mandatory.** Pad the bar's bottom by the home-indicator inset (`env(safe-area-inset-bottom)` on web, `safeAreaInsets.bottom` on iOS, `WindowInsets.navigationBars` on Android). Content sitting flush against the indicator looks broken and is hard to tap.
- **Reserve the scroll container's bottom padding** equal to the bar's height plus the inset, so the last item of content is reachable rather than permanently hidden behind the bar.
- **Keyboard — and the platform asymmetry matters.** The bar must move above the keyboard, not be covered by it. On **iOS this is largely free**: SwiftUI applies keyboard avoidance by default (opt out with `ignoresSafeArea`), and UIKit has `keyboardLayoutGuide`. On **Android it is your job**: read `WindowInsets.ime` and apply `imePadding()`. Since Android 15 (API 35) enforces edge-to-edge for apps targeting SDK 35, a bottom bar relying on `adjustResize` alone will sit *under* the keyboard. If the bar's action isn't relevant to text entry, hide it while the keyboard is up rather than stacking two bars.
- **The bottom edge is a system gesture zone**, not just a safe area — Home and app-switcher gestures live there, and Apple warns that controls placed at the very bottom edge invite taps that cannot land. Aligning to the bottom of the safe area is what keeps your action from competing with them.
- **Don't run it full-width edge-to-edge.** Baymard's one published sticky-CTA guideline is that the button should *not* be full-width and should carry surrounding white space; a full-bleed button reads as chrome and loses the separation that marks it as primary.
- **Elevation:** a hairline top border or a soft shadow only when content scrolls beneath it. A permanently heavy shadow reads as chrome.
- **One primary per bar.** A secondary action can share the bar only at clearly lower weight (text button beside a filled button). *(Design judgment — no published research tests this specific rule.)*
- **Disabled state carries the reason.** `Continue` greyed out with no explanation is a dead end; pair it with the blocking condition ("Select a date to continue") in the bar or immediately above it.
- **Completability is the whole mechanism.** In the clearest public A/B test, the sticky variant that merely *scrolled the user to* the real control showed no statistically significant lift over no sticky bar; only the variant completing the action in place moved orders. If your bar is a shortcut to the action rather than the action, it is paying viewport rent for nothing.

---

## Thumb reach

**Source and its limits, stated up front.** The canonical data is Steven Hoober's 2013 UXmatters observation of 1,333 people (780 actively touching a screen): **49% one-handed, 36% cradled, 15% two-handed**. Two cautions before using any of it:

1. **The famous "75% thumb-driven" figure does not appear in Hoober's article.** It is reconstructed arithmetic — 49% + (36% × 72% cradling-with-thumb) ≈ 74.9% — and describes the share using a *single thumb*, not the share of thumb-driven interaction. Counting all thumb use including two-handed gives roughly 90%. Cite it as "~75% use a single thumb", or don't cite it.
2. **This is 2013 data from the era of 4–5″ phones, and no field replication on modern 6.5″+ devices was found.** The familiar three-zone heat map is Scott Hurff's 2014 derivation, not Hoober's original. The direction holds — thumbs dominate, far corners are hard — but treat specific zone boundaries as directional, not measured.

The zones, understood as an **arc, not a horizontal band** — the comfortable region is a rotation around the thumb joint, so it cuts diagonally and shrinks toward the far top corner as screens grow:

- **Easy** — the arc the thumb sweeps from its anchor, covering the lower portion and the bottom corner on the holding-hand side. Put primary actions, tab bars, and frequently repeated controls here.
- **Stretch** — the middle band. Fine for content and occasional controls.
- **Hard** — the far top corner, requiring the user to shift the device in hand. Both platforms ship mitigations for exactly this (iOS Reachability, Android/OEM one-handed modes). Never put a frequently used or destructive-to-miss control there.

Consequences: a top-right `Save` on a long form is a reach failure — F2's argument restated ergonomically. Back buttons live top-left by platform convention and are exempt because the edge-swipe / system-back gesture is the real path.

**Do not assume handedness — this is the best-supported claim in the section.** Grip flips with posture inside the same population: among one-handed users Hoober found 67% right thumb / 33% left, but among those *cradling* the device, 79% cradled in the **left** hand. Same people, opposite dominant side depending on posture. Users also switch grips constantly — sometimes every few seconds — as the task shifts between scrolling, reaching, and typing. There is no stable holding side to design toward; symmetric layouts are the only safe default, and you should design for the *transition* rather than for one posture.

---

## Touch targets and hit areas

- iOS: **44×44 pt** hit region. Android / Material: **48×48 dp**. Apple's minimum *visible* control is smaller — 28×28 pt — so these are two different measurements, not one.
- The visual size may be smaller than the target: expand the touch bounds rather than inflating the glyph. Compose does it automatically via `minimumInteractiveComponentSize`; Android Views use `TouchDelegate`; React Native calls it `hitSlop` (an RN term, not a platform standard). Steppers, chips, and icon-only nav buttons are the usual offenders.
- **Separation: ~12 pt around bezeled elements, ~24 pt around unbezeled ones.** These are Apple's figures, and they are 1.5–3× what most designs ship — an earlier draft of this file said 8 pt, which is sourced to nothing. A `−`/`+` stepper with touching buttons is a mis-tap generator, and the mis-tap is expensive when it changes a quantity or a price.
- **On the web the tested numbers are different again:** WCAG 2.5.8 (AA) requires 24×24 CSS px, with a Spacing exception that passes an undersized target when a 24 px circle centered on it clears every neighbor; 2.5.5 (AAA) requires 44×44 CSS px and has no such exception.

---

## Presets (F3)

**Read this first: presets are an anchor, and the anchor moves money.** Haggag & Paci (*AEJ: Applied* 2014) analysed 13M+ NYC taxi rides across a fare threshold where suggested tips jumped. Raising the suggestions raised tips by more than 10% at the margin — but *also* made riders **over 50% more likely to leave nothing at all** (1.7 and 2.8 percentage points absolute), which the authors attribute to reactance: users perceiving the defaults as manipulation and punishing them. The authors frame their own paper as documenting default effects exploited by a for-profit industry. Use presets to cut effort toward values users already want; the other use is a dark pattern with a measurable backlash.

- **Derive from the usage distribution — critically.** Pull the top 2–3 actual values, not round numbers. If the distribution is flat, presets don't help — skip them rather than inventing three.
- **Beware the ratchet.** Defaults shape the distribution later used to justify them, so re-deriving presets from post-preset usage drags values upward each cycle. Source from pre-preset behavior or from the custom-entry path where you can.
- **Order them by frequency**, left to right, so the most common is nearest the natural thumb start.
- **Show which preset is active**, and clear the selection when the user edits the custom control — a preset chip that stays highlighted after a manual change misreports the state (D4 again).
- **Presets are not a segmented control** unless they're exhaustive. If a custom value is possible, the presets are shortcuts and must not visually claim to be the complete set of options.
- Re-derive periodically, and **audit for drift in both directions**. A set frozen at launch drifts from real behavior; a rising share of users bypassing the presets or abandoning entirely means they have drifted from assisting into extracting.

---

## Font scale and Dynamic Type

- Test at the platform maximum, including the accessibility sizes (iOS AX1–AX5, Android 200%).
- Fixed-height rows break first. Prefer intrinsic height with a minimum, not a fixed height.
- **Decision-critical text must never truncate** — price, total, error reason, permission justification. Let it wrap and push layout; truncate labels and descriptions instead.
- Horizontal chip/preset rows should wrap or scroll at large scales rather than shrinking their text.
- Check the sticky bar and the promoted nav title specifically — both have constrained height and both carry decision-critical text.

---

## Scope limits on contested rules

Where a rule in `SKILL.md` is stated as a default rather than a finding, the reasoning lives here. Read this before overriding the rule *or* before defending it hard.

### D5 — "price early"

What the evidence actually supports: **presence and findability**, not a scroll depth. NN/g's *State the Price* reports that pricing is the top information need business customers name and that participants leave for competitors when it is absent — the failure is withholding, not ordering. No published study fixes the depth at which price must appear.

Where it comes from matters more than most citations of it admit: the strong price-first evidence is from **comparison contexts** — e-commerce browsing, B2B evaluation — where price is a filter criterion the user is actively screening on. A paywall is a **commitment context**: the user is deciding whether this thing is worth anything at all, and price is the last input, not the filter.

So the honest position on paywalls is a gap, not a rebuttal. The subscription-app literature does argue value-before-price, but every source located argues it about *when the paywall appears in the funnel* (after onboarding, at peak motivation, after a core action completes) — not about the ordering of value and price **within a single screen**, which is the variable this rule is about. Those sources are also paywall vendors publishing marketing content, not independent research. The within-screen question appears untested in public literature.

Practical consequence for a review:
- **Price hard to find, or discoverable only by scrolling past unrelated content** → defect, call it.
- **Price placed after a value pitch on a paywall, but plainly visible without hunting** → defensible; do not flag it as a D5 violation.
- **Comparison surfaces** (listings, plan grids, search results) → price early is a strong default, because the user is screening.

Related: NN/g's *Scrolling and Attention* (2018, 120 participants, 130,000+ fixations) found ~57% of viewing time above the fold and 74% within the first two screenfuls. That justifies "position predicts attention"; it does not justify a specific cutoff.

---

## Sources

Primary sources this file's numbers come from. Where a figure is a craft default with no published backing, it is marked as such inline above rather than listed here.

**Platform**
- Apple HIG — [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) (44×44 pt hit region / 28×28 pt minimum control; ~12 pt padding around bezeled elements, ~24 pt unbezeled; contrast table), [Typography](https://developer.apple.com/design/human-interface-guidelines/typography) (iOS Body 17 pt at default Dynamic Type), [Layout](https://developer.apple.com/design/human-interface-guidelines/layout) (safe areas, bottom-edge gestures), [SF Symbols](https://developer.apple.com/design/human-interface-guidelines/sf-symbols) (nine weights for text weight-matching; fill variant indicates selection; tab bar prefers fill, toolbar takes outline), [Status bars](https://developer.apple.com/design/human-interface-guidelines/status-bars)
  - *Note: HIG pages are JS-rendered SPAs. Fetch the backing DocC JSON at `developer.apple.com/tutorials/data/design/human-interface-guidelines/<page>.json` to read the real text.*
- [Material Symbols](https://developers.google.com/fonts/docs/material_symbols) — `opsz` axis 20–48dp; fill axis for state transitions
- [Material Components Android — TopAppBar](https://github.com/material-components/material-components-android/blob/master/docs/components/TopAppBar.md) and [`CollapsingToolbarLayout.java`](https://github.com/material-components/material-components-android/blob/master/lib/java/com/google/android/material/appbar/CollapsingToolbarLayout.java) — `DEFAULT_PARALLAX_MULTIPLIER = 0.5f`; title collapse modes; 600ms scrim animation
- [Material Design 1 — Imagery](https://m1.material.io/style/imagery.html) — scrim opacity 20–40% dark / 40–60% light (deprecated spec; no M3 successor guidance found)
- [Compose window insets](https://developer.android.com/develop/ui/compose/layouts/insets) and [system bars](https://developer.android.com/develop/ui/compose/system/system-bars) — `WindowInsets.ime`, `imePadding()`, SDK 35 edge-to-edge enforcement
- [Android 14 non-linear font scaling](https://developer.android.com/about/versions/14/features#non-linear-font-scaling) — 200% maximum *(verified for Android 14; not re-verified for 15/16)*

**Standards**
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) — [1.4.3 Contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) · [1.4.12 Text Spacing](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html) · [2.5.3 Label in Name](https://www.w3.org/WAI/WCAG22/Understanding/label-in-name.html) · [2.5.8 Target Size (Min)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) · [3.3.2 Labels or Instructions](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html) · [4.1.3 Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) · [F83](https://www.w3.org/TR/WCAG20-TECHS/F83.html) (text over background images)
- [MDN — ARIA live regions](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions) — headings are not live regions
- *SC 4.1.1 Parsing is obsolete and removed in WCAG 2.2 — guidance still citing it is stale.*

**Research**
- [NN/g — Product Photos on Listing Pages](https://www.nngroup.com/articles/product-photos-listing-pages/) — consistency is of *style*, not identity; contextual imagery is one of six qualities
- [NN/g — Scrolling and Attention](https://www.nngroup.com/articles/scrolling-and-attention/) — 2018, 120 participants, 130k+ fixations; ~57% of viewing time above the fold
- [NN/g — Placeholders in Form Fields Are Harmful](https://www.nngroup.com/articles/form-design-placeholders/) — the failures that removing a visible label reproduces
- [NN/g — Closeness of Actions and Objects](https://www.nngroup.com/articles/closeness-of-actions-and-objects-gui/) · [Inverted Pyramid](https://www.nngroup.com/articles/inverted-pyramid/) · [State the Price](https://www.nngroup.com/articles/show-price/)
- Haggag & Paci, *Default Tips*, [AEJ: Applied 2014, 6(3):1–19](https://www.aeaweb.org/articles?id=10.1257/app.6.3.1) — preset anchoring and the reactance backlash
- Hoober, [How Do Users Really Hold Mobile Devices?](https://www.uxmatters.com/mt/archives/2013/02/how-do-users-really-hold-mobile-devices.php) UXmatters 2013 — 1,333 observed; grip distribution
- [GOV.UK Design System — Button](https://design-system.service.gov.uk/components/button/) — sentence case; outcome-bearing labels

**Debunked — do not cite these**
- *"Baymard: sticky add-to-cart lifts conversion 5–12%."* No such figure exists in Baymard's published guidance. Their only sticky-CTA guideline is that the button should not be full-width and should carry white space.
- *"NN/g: keep sticky headers under 10% of viewport height."* Not in the NN/g sticky-headers article.
- *"Hoober: 75% of users are thumb-driven."* Absent from the article; see the Thumb reach section for what the numbers actually are.
- *"Use CSS `text-transform` so screen readers don't spell out all-caps."* Browsers have exposed transformed text to the accessibility tree as uppercase; this is not a reliable workaround.
