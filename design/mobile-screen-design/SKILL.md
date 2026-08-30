---
name: mobile-screen-design
description: Manual-only mobile screen design pass, invoked with /mobile-screen-design. Runs a defect pass (overlay contrast, media systems, icon consistency, mutable state in copy, decision-order, action grouping) then a flow pass (scroll context, action availability, common-case shortcuts) over any mobile app screen — detail, settings, profile, onboarding, checkout, paywall.
disable-model-invocation: true
---

# Mobile Screen Design

Two passes, in order. The first removes defects. The second makes the screen easier to use. **Most redesigns stop after the first pass and ship a clean screen that is still tiring.** Do not stop there.

Every rule below is stated for mobile app screens generally — a product detail page is only one instance. Apply them to settings, profiles, onboarding steps, paywalls, filter sheets, listings, and forms.

## Mode

**If no screen was supplied** — no screenshot, file path, component code, or written description — ask for one and stop. Do not invent a generic screen to critique.

Otherwise classify the request as exactly one of these before applying anything. If ambiguous between Review and Build, treat it as Review — do not redesign something the user asked you to critique.

**Review** — critique an existing screen (screenshot, code, or description).
Output: numbered findings, most severe first. Each finding must (a) carry its rule tag — `[D1]`…`[D7]`, `[F1]`…`[F3]`, or `[C]` for the craft baseline; (b) name the specific element at fault; (c) pair the problem with a concrete fix, not a judgment. Cover both passes. If a pass yields no findings, say so in one line rather than omitting it.

**When a rule cannot be evaluated from the material provided, say so and name what you would need** — do not fabricate a finding and do not drop the rule silently. A single screenshot cannot show you the other media the surface can receive (D1), the sibling set the asset will sit in (D2), the usage distribution behind a preset (F3), or hit-area and font-scale behavior (`[C]`). List those as *unevaluated* with the missing input beside each.

A bare design question is answered the same way, minus the numbering: give the recommendation, name the governing rule, state the reasoning.

**Build** — create or extend a mobile screen.
Output: design the Pass 2 affordances (sticky action, collapsing header, presets) *before* writing markup — they determine component structure and cannot be bolted on. Run the Build gate at the end. Every gate item is satisfied or explicitly flagged as an open issue; a silent pass is a failure.

---

## Pass 1 — Defect pass

### D1. Overlay controls must survive the content beneath them, not this one asset

Any control layered over content you do not control — back/share/save over a hero image, captions over video, controls over a map, a FAB over a feed, status-bar glyphs under a full-bleed header — is only legible by accident if its contrast comes from the current asset.

Test against the extremes the surface can actually receive: brightest, darkest, busiest, and lowest-contrast-in-the-corner. A white icon that works on a dark photo vanishes on a pale one.

Fix: give the control its own contrast source — a scrim or filled container behind it, sized and shaped independently of the asset. This is the part platform guidance actually prescribes (Material's original imagery spec calls for scrims; Apple prefers a blurred view behind the status bar). An outline or shadow on top is reasonable belt-and-braces, but it is not the mechanism.

**The acceptance test, not a magic opacity.** WCAG covers this only for the asset in front of you: failure technique F83 tests text against the lightest or darkest region of a *specific* background image, and 1.4.11 Non-text Contrast requires 3:1 for icon controls against adjacent colors. Neither requires contrast to survive an upload you have not seen. So adapt F83 forward: the control must clear **4.5:1 for text and 3:1 for glyphs against the lightest region the surface can ever receive**. Pass there and you pass everywhere. Verify by rendering with the media replaced by pure white, then pure black, then a high-frequency image.

Apple's own rule is blunter than "make it legible": obscure content under the status bar, or hide the bar entirely during full-screen media rather than fighting the image.

*Non-commerce:* a profile screen's edit button over a user-uploaded cover photo; a map screen's recenter button over satellite tiles; a story viewer's close button over arbitrary video frames.

### D2. Media is chosen for the set, not for the screen

An image never lives alone. It sits in a grid, a list, a carousel, a search result — beside siblings. Judge every asset in that context.

- **Consistency is about style, not plainness.** NN/g's listing-page research is explicit that images need not be identical — they must be consistent *in style*, which is what makes a set scannable and comparable. A set can carry diverse poses, backgrounds, and models and still cohere if one visual convention governs it. Do not read "consistent" as "cut out on white."
- **Context is load-bearing for anything judged by fit, scale, or setting.** Apparel, accessories, cosmetics, furniture: NN/g lists *contextual* among its six qualities of a good listing image, and Baymard's testing finds on-model shots necessary where users must judge fit or how a shade reads on skin. A cut-out suppresses information those users need. Pick one treatment per category — contextual or clean — and hold it.
- **But context must not steal the subject.** NN/g's counter-example is a retailer whose full-length outfit shots made it hard to tell which garment was actually for sale. Context that obscures which item is featured is a defect; the eye must still land on the right noun.
- **The media should depict the unit the copy describes.** One item pictured beside a by-weight price invites a misread; one screenshot for a multi-screen feature, one avatar for a group. *(Practitioner heuristic — no published study located. The nearest evidence is Baymard's finding that users misjudge physical size without an in-scale reference.)*
- **Beware backgrounds that contradict the claim.** Artificial styling under a "natural / honest / real" positioning is a representational lie.
- **One image per item is usually too few.** Baymard recommends several thumbnails per list item. Consistency governs which image *type* occupies the default slot across the set — it does not mean each item gets only one image.

*Non-commerce:* team avatars in a member list, cover art in a library, illustration sets across onboarding steps, empty-state art across an app. Same test — line them up and look for the one that breaks the system.

### D3. Icons in a set share one visual logic

Icons that vary **without a rule** — stroke weight drifting between sets, fill applied ad hoc, accent colors accumulating one feature at a time — read as decoration rather than information, and their combined weight competes with the screen's actual subject. The defect is unruled variation, not variation.

Fix: **one rule per axis, not one value.** Both platforms ship these as variable axes with documented purposes, so freezing them is its own error:

- **Stroke weight matched to adjacent text weight.** SF Symbols ships nine weights corresponding to San Francisco's, expressly for "precise weight matching between symbols and adjacent text." A UI with several text weights therefore has several symbol weights — by rule, not frozen.
- **Optical size tracks render size.** Material Symbols' `opsz` axis spans 20–48dp so apparent stroke weight stays constant as icons scale. Pinning one optical size produces the inconsistency the axis exists to prevent.
- **Fill is a state signal, not a taste call.** Apple: use the fill variant "to indicate selection" — an iOS tab bar prefers fill, a toolbar takes outline. Material's fill axis is documented for conveying state transitions. A blanket "one fill convention" would forbid the standard iOS tab bar idiom.
- **One corner language**, and one accent color for interactive state — additional hues reserved for semantic meaning (status, category, warning) rather than decoration.

Then tighten spacing so the row reads as a single unit rather than six competing marks.

*Non-commerce:* settings-row leading icons, tab-bar glyphs, permission-request icon sets, achievement badges.

### D4. Mutable state must not live in static copy

If a control on the screen can change a value, that value must not be baked into a title or heading — the heading starts lying the moment the user taps.

The classic case: a title reading "Strawberries 1 kg" above a quantity stepper. The instant the user increments it, the title is false.

Rule: the title names the invariant thing. The mutable value lives adjacent to the control that changes it, with exactly one source of truth.

**The sharper reason is accessibility, not aesthetics.** A bound heading updates correctly on screen — but assistive technology announces dynamic changes only inside a *declared live region*, and a heading is not one. A sighted user watches the total tick from $48 to $64; a screen-reader user who already passed that heading gets silence. Put a recalculating value in a `role="status"` region and mark the whole string so the announcement carries its own context (WCAG 4.1.3 Status Messages, AA).

*Non-commerce:* a settings header reading "3 devices connected" above an editable device list; a profile heading with a follower count that the Follow button on the same screen changes; a filter chip permanently labeled with its default value; an onboarding step titled "Step 2 of 4" in a flow whose length varies by answer.

### D5. Decision-critical information goes above the decision

A mobile screen is a single-column queue, not a canvas. The governing published principle is the **inverted pyramid** — conclusion first, elaboration after, because users scroll only when what they've already seen looks promising. Position predicts attention: NN/g's 2018 eye-tracking study (120 participants, 130,000+ fixations) found ~57% of viewing time above the fold and 74% within the first two screenfuls.

Order the queue by the questions the user is actually asking. *(The specific four-question sequence below is a working heuristic, not a research finding — don't cite it as one.)*

1. **What is this?** — identity: title, primary media.
2. **Can I trust it?** — trust signals belong *adjacent to the identity they qualify*, never in a distant section. Rating and review count next to the title; verification badge next to the name; the security note next to the field that needs it.
3. **What does it cost me?** — price, time, permissions, data required. Price is among the first things users look for, and its absence sends them to competitors (NN/g). Strong default, not a measured threshold — and a **paywall is the one screen where value-before-price is a defensible strategy rather than a defect**. See *Scope limits* in `references/mobile-patterns.md` before calling it either way.
4. **What do I do?** — the action.

Anything the user needs in order to decide, placed below the fold of that decision, forces a scroll-and-remember loop. That loop is the cost you are removing.

*Non-commerce:* a paywall where the price is genuinely hard to *find* — not merely placed after the value pitch, which is the defensible version; a permission prompt whose justification sits below the Allow button; a download button whose file size appears in a detail section; a settings toggle whose consequence is explained three rows down.

### D6. Group a control with the action it parameterizes, and put the consequence in the action

If a control shapes what the action will do, the two belong side by side, and the resulting outcome belongs inside the action itself. The user must be able to read the exact consequence without leaving the button's line of sight.

- Quantity stepper adjacent to the button, unit inside the stepper, resulting total inside the button.
- Plan selector adjacent to `Subscribe · $9/mo`, not a screen away from it.
- Date range adjacent to `Book · 3 nights`.
- Recipient picker adjacent to `Send`; destination adjacent to `Move to Archive`.

Separately: **the primary action does not need to shout.** Set button text in sentence case — all-caps flattens words into uniform rectangles and removes the shape cues readers scan by; GOV.UK's design system specifies sentence case for the same reason. The button only has to be unambiguously the heaviest element in its region.

*Don't repeat the folklore:* no WCAG criterion forbids all-caps (the supporting W3C material is the COGA note, which is advisory, not normative). And the popular fix — "author sentence case, uppercase with CSS `text-transform`, screen readers stay safe" — is not reliable either: browsers have exposed transformed text to the accessibility tree as uppercase, and VoiceOver has been observed reading a CSS-uppercased short word as an initialism. The durable reason to avoid all-caps is legibility, not screen readers.

### D7. Badges and labels are scanned, not read

- **Cut every word the format already carries.** "Price: $4.99" → "$4.99" — a currency symbol already says "price." "20% OFF DISCOUNT" with a tag icon → "20% off". A badge that takes a second to parse has failed at being a badge.
- **Drop icons that restate adjacent text.** Duplicate encoding; keep one.
- **Small uppercase needs letter-spacing.** Capitals have low shape variety, so generous tracking is what lets the eye separate them — settled typographic practice rather than a measured UI finding. Then test with *user* text-spacing applied: WCAG 1.4.12 (AA) requires no loss of content when the user adds 0.12× the font size on top of yours, and fixed-width pills are exactly where that breaks.
- **Label consistently or not at all.** If one field gets a visible label for clarity, its peers need one too — inconsistent labeling is worse than none.
**Before cutting any label, ask what the element does — the three cases have three different answers:**

- **Display value → cut freely.** "Price: $4.99" → "$4.99" takes no user input, so no criterion is implicated.
- **Form input → never strip the visible label.** An `aria-label` is *not* a substitute. W3C is explicit that a control can use `aria-label` and "therefore pass Success Criterion 4.1.2, but ... still fail this success criterion (if the labels or instructions aren't presented to all users, not just those using assistive technologies)" — SC 3.3.2 Labels or Instructions (Level A). Removing it recreates the documented placeholder-as-label failures: users can't review answers before submitting, can't recover from errors, and can't recall what a filled field asked. The people harmed are exactly those an accessible name does nothing for — sighted users with cognitive, memory, or low-vision needs.
- **Icon-only control → accessible name keeps you conformant, not understood.** Once no visible text exists, SC 2.5.3 Label in Name "does not apply to that component" — so nothing is left checking that what a user sees matches what a speech-input user can say. Pair the icon with a visible label wherever its meaning isn't already conventional.

*Non-commerce:* a permission dialog reading "Allow: Allow camera access"; a settings row labeled "Setting: On" beside its own toggle; a notification chip reading "New · NEW".

---

## Pass 2 — Flow pass

Pass 1 gets you a clean screen. Pass 2 asks what the screen still *makes the user do*. Count the taps, the scroll-backs, and the moments where they must hold a value in their head. That count is your backlog.

### F1. Preserve context across the scroll

When a screen opens with identity (media + title) and continues into detail, the user loses the answer to "what am I looking at" the moment they scroll past it.

Pattern: the content sits in a card that slides up over the media, so the media stays visible while it still matters; once it scrolls away, the title promotes into the nav bar and stays. Context is never lost, and no vertical space is spent on a header that duplicates what is already on screen.

Applies to any identity-then-detail screen: profiles, articles, events, listings, settings sub-pages, order detail.

### F2. Keep the primary action available at the moment of intent

Intent forms at scroll positions you cannot predict in advance, so an action anchored at one fixed position is only conveniently available to the users who happen to decide there. Treat that as design rationale, not a measured finding — the evidence is outcome-level, not a measurement of where intent forms.

Pattern: a sticky bottom action area holding the primary action *and* the control that parameterizes it (see D6), respecting the bottom safe-area inset.

Applies to: `Save` on a long form, `Apply` on a filter sheet, `Book` on a listing, `Continue` in a multi-step flow.

**Completability is the mechanism, not stickiness.** In the clearest public A/B test, a sticky button that merely *scrolled the user to* the real control measured no better than no sticky bar at all; only the variant that completed the action in place (a slide-up drawer) moved orders. A sticky bar that is a shortcut *to* the action earns nothing.

**Calibrate your confidence.** The strongest public data is a single site, single vertical, 14 days: ~+5.2% completed orders on mobile, +7.9% on desktop, at high significance. That is real but not a general law. The widely-repeated "5–12% uplift per Baymard" figure **does not exist** in Baymard's published guidance — Baymard's only sticky-CTA guideline is that the button should *not* be full-width and should carry surrounding white space. Do not cite the phantom number.

**Reversals — do not stick it when:**
- **The action isn't yet takeable.** A bar reading `Add to cart` before a required variant is chosen either lies or bounces the user up the page. Carry enough state in the bar to complete the action, or don't pin it yet — and if disabled, show the blocking reason.
- **There is more than one candidate for primary.** Pick one. *(Design judgment; no published research tests this specific rule.)*
- **The screen is short enough that the action never leaves the viewport.** Sticky chrome permanently subtracts from the content area, which bites hardest on the smallest screens.

**The bottom edge is a gesture zone, not just a safe area** — Home and app-switcher gestures live there. Aligning to the bottom of the safe area is what keeps your primary action from competing with them.

### F3. Make the common case one tap, keep the general case reachable

If a control requires repeated interaction to reach a value most users want, offer that value as a preset.

- Quantity: `500 g` / `1 kg` / `2 kg` chips beside the stepper.
- Tips, transfer amounts, snooze durations: presets beside the custom field.
- Dates: `Today` / `Tomorrow` beside the picker.

**Presets are not a neutral convenience — they are an anchor, and the anchor moves money.** In the canonical study (Haggag & Paci, *AEJ: Applied* 2014, 13M+ NYC taxi rides), raising suggested tips raised average tips by more than 10% at the margin. The authors frame their own paper as documenting default effects exploited by a for-profit industry. Design presets to reduce effort toward values users already want — not to drag them upward.

Three conditions:

1. **Presets come from the actual usage distribution** — but read that distribution critically. Defaults *shape* the distribution later used to justify them, so naively re-deriving presets from post-preset usage ratchets values upward each cycle. Where possible, source from behavior recorded before presets existed, or from the custom-entry path rather than preset taps.
2. **Never remove the general path to add the shortcut.** The custom control stays. When the preset row crowds out the values users actually want, they don't comply — they read it as manipulation and opt out. In the taxi data, higher suggestions made riders **over 50% more likely to leave nothing at all** (1.7 and 2.8 percentage points absolute), which the authors attribute to reactance.
3. **There is a ceiling.** Past the point users judge fair, they don't pick a lower preset — they abandon the interaction. Audit preset rows periodically: a rising share bypassing them or opting out means the presets have drifted from assisting into extracting.

---

## Craft baseline

Generic visual-craft rules. These matter, but they are not what distinguishes mobile work — apply them quickly and defer to the sibling skill `tufte-clarity` for the underlying principle when a judgment call is contested. Tag all of these `[C]` in Review output.

- **One margin, held screen-wide.** Pick 16/20/24 and align every text block, icon, price, and section to it. Users don't consciously notice misalignment; they feel the screen as less trustworthy.
- **One type family.** Build hierarchy from size, weight, color, and line-height — not from a second font.
- **Do not invent a body-size floor — adopt the platform text style.** iOS Body is 17 pt at the default Dynamic Type size; Material 3 Body Medium is 14 sp. A blanket "16 pt minimum" is a web convention that is below Apple's default and above Material's. In *web views* only, keep body and input text at ≥16px: below that iOS Safari has long zoomed the viewport on input focus — widely reproduced but undocumented by Apple, so verify on device.
- **Don't hardcode line-height; survive the user's override.** The familiar 1.5 figure is WCAG 1.4.12 Text Spacing (AA) — a resilience requirement, not a design target. Nothing may clip or overlap when a user forces line height to 1.5×, paragraph spacing 2×, letter spacing 0.12×, word spacing 0.16×.
- **Body contrast never below 4.5:1** (WCAG 1.4.3, AA). The 3:1 relaxation covers only large text — 18 pt, or 14 pt bold — so it never applies to body copy. Headlines attract; paragraphs support.
- **Palette supports the content.** Reserve saturation for the primary action and genuine status. A screen where five things compete has no hierarchy.
- **Dividers at the lightest weight that still separates** — often none, because spacing already did the job. Heavy rules chop one experience into harsh blocks.
- **Spacing encodes relationship.** Related elements close, unrelated apart. Too much whitespace disconnects as surely as too little crowds — whitespace is a statement about grouping, not a supply of air.
- **Hit region ≥ 44×44 pt (iOS) / 48×48 dp (Android)**, even when the drawn control is smaller — Apple's minimum *visible* control is 28×28 pt, and the 44 pt figure governs the touch region. Pad the touch bounds rather than inflating the glyph (Compose does this via `minimumInteractiveComponentSize`; Android Views use `TouchDelegate`). Steppers, chips, and icon-only nav buttons are the usual offenders.
- **Separate adjacent targets.** Apple advises ~12 pt of padding around bezeled elements and ~24 pt around unbezeled ones — roughly 1.5–3× what most designs ship. Touching `−`/`+` stepper buttons generate mis-taps, and the mis-tap changes a quantity or a price.
- **On the web these are conformance requirements, not guidance.** WCAG 2.2 SC 2.5.8 Target Size (Minimum, AA) requires 24×24 CSS px; SC 2.5.5 (Enhanced, AAA) requires 44×44. An undersized target still passes 2.5.8 under its Spacing exception when a 24 px circle centered on it clears every neighbor — 2.5.5 has no such exception. Note 2.5.5's 44 px and Apple's 44 pt coincide numerically but are different units and different kinds of rule.
- **Respect system-defined safe areas** rather than hardcoding insets. Content must clear the Dynamic Island / camera housing, the bottom inset, and the display's corner radius. In landscape those hardware features move to a *side* edge, so verify both rotation directions. ("Notch" and "home indicator" are no longer current HIG vocabulary.)
- **Test at the platform maximum font scale** — iOS `DynamicTypeSize.accessibility1`–`accessibility5`, Android 200%. Since Android 14 scaling is *non-linear*: small text grows faster than large, so a layout that survives at 200% in its headings can still break in its captions. Check the smallest type styles first, and never let decision-critical text truncate.

---

## Build gate

Run before presenting a Build deliverable. Satisfy each item or flag it explicitly as an open issue.

1. Does every overlay control clear 4.5:1 (text) / 3:1 (glyphs) against the *lightest region the surface can ever receive* — verified against pure white, pure black, and a busy image? `[D1]`
2. Do assets share a consistent *style* beside their siblings, with context retained where fit/scale/setting must be judged, and the featured item still unambiguous? `[D2]`
3. Does each icon axis follow a *rule* — weight matched to adjacent text, optical size tracking render size, fill reserved for state — rather than a frozen value? `[D3]`
4. Is every value a control can change absent from static headings, on one source of truth, and announced via `role="status"` rather than silently? `[D4]`
5. Are identity, trust signal, cost, and action all reachable before the long tail of detail? `[D5]`
6. Is each parameterizing control adjacent to its action, with the resulting consequence shown inside the action? `[D6]`
7. Is every badge stripped to what is scannable — and did you check the element *type* first (display values cut freely, form inputs keep their visible label, icon-only controls keep an accessible name)? `[D7]`
8. Does context survive the scroll — collapsing header or sticky title? `[F1]`
9. Can the sticky action be *completed in place* (not merely scrolled to), and does it pass the F2 reversals and clear the bottom gesture zone? `[F2]`
10. Are presets sourced from uncontaminated usage data, aimed at values users already want rather than upward, with the custom path retained? `[F3]`
11. Craft baseline: single margin, one type family, platform text styles, hit regions + target separation, safe areas, max font scale. `[C]`
12. States present: empty, loading, error, and disabled-action-with-reason.

Load `references/mobile-patterns.md` for two things: **platform mechanics** (overlay contrast techniques, collapsing-header and sticky-bar implementation, thumb-reach zones, safe areas, preset selection), and **scope limits** — the reasoning behind rules stated as defaults rather than findings, which is what you need before overriding one *or* defending it hard. It also carries the primary sources for every number in this skill, plus a **debunked list** of widely-repeated figures that do not exist in the sources they are attributed to.

## Evidence status

Rules here are not equally grounded. Say which kind you are invoking when a finding is contested:

- **Platform-documented** (cite freely): D1 scrim mechanism, D3 icon axes, hit regions and target separation, safe areas, font scaling, every WCAG criterion named.
- **Research-backed**: D2 style-consistency and contextual imagery (NN/g), D5 position-predicts-attention (NN/g eye-tracking), D7 form-label harm (WCAG 3.3.2 + NN/g placeholder research), F3 preset anchoring (Haggag & Paci).
- **Thin or single-source** — state the limit when you rely on them: F2 sticky-bar uplift (one site, one vertical, 14 days), thumb-reach zones (2013 data, 4–5″ phones, no modern replication).
- **Practitioner heuristic, no published study**: D4's rule, D5's four-question ordering, D6's grouping, the F1 card-over-media composition, "one primary per bar". These are reasonable and cheap to follow — just don't present them as findings.

## Related skills

- `tufte-clarity` — the general information-design principles behind the craft baseline (signal-to-chrome, duplicate encoding, visual hierarchy, necessity test).
- `dashboard-design` — data-dense product UIs: tables, list views, metrics, progressive disclosure.
