---
name: hairline-ui
description: Manual-only, invoked with /hairline-ui. Applies the shortener admin's UI style and motion to another app: flat neutral grays, hairline borders, tints instead of shadows, light and dark mode, plus its animation system (sliding segmented thumb, grid-rows disclosure, in-place copy confirmations, row enter/exit and FLIP, toast queue, dialog and view transitions, reduced-motion fallbacks). Copy-ready tokens, component CSS and JS helpers.
disable-model-invocation: true
---

Use this style for any UI built or restyled in this task. It extends `/ui-style` with dark mode, contrast-checked text colours, touch sizing and a full motion system, all taken from the pothonon.party shortener admin.

If the project already has a design system, ask before overriding it. If it uses a framework (React, Svelte, Tailwind), keep the CSS variables as the source of truth and map them into the framework's theme rather than rewriting values.

## Files

| File | What it holds | How to use it |
|---|---|---|
| `references/tokens.css` | Colours, radii, shadows, type, motion timings, light + dark + touch | Copy as-is to the top of the stylesheet. Never edit values per component. |
| `references/components.css` | Base, cards, inputs, composer, buttons, swaps, segmented control, checkbox, disclosure, rows, tiles, badges, skeleton, dialog, toast, view transitions, reduced motion | Copy the blocks you need. The base block and the reduced-motion block are always required. |
| `references/motion.js` | `markReady`, `flash`, `confirmDone`, `setReveal`, `swap`, `enterRow`/`exitRow`, `flip`, `pop`, toast queue | Copy the helpers you use. No dependencies. |
| `assets/demo.html` | Every component and motion on one page | Open it to see the target look, and to compare your result against it. |

Read the comment above each block in `components.css` before using it: it gives the expected markup.

## Workflow

1. Read `tokens.css` and paste it in. Then read `components.css` and `motion.js` and take what the screens need.
2. Rename classes only to match the app's existing naming. Keep the structure, values and timings.
3. Build screens from the components. When something new is needed, compose it from tokens using the rules below; don't invent new colours, shadows or durations.
4. Check the result against the checklist at the end, in light mode, dark mode, at 375px width, and with reduced motion turned on. If Playwright is available, screenshot both colour schemes (`colorScheme: "dark"`) and compare with `assets/demo.html`.

## Look

1. **Neutral only.** Every gray is black-at-alpha in light mode and white-at-alpha in dark mode, so it works on any surface. No brand hue in chrome. Status colours (`--danger`, `--warn`, `--ok`) colour text only, never fills.
2. **Hairlines, not boxes.** Borders are 1px at 8–12%, usually drawn as `box-shadow: 0 0 0 1px` so they don't shift layout. Inputs and checkboxes are the exception: `--border-input` (45%) so people can see where to type.
3. **Tints for state.** Hover adds `--tint-hover` (+5%), selected or pressed adds `--tint-selected` (+10%). A control on a hovered row steps from +5% to +10%. No lift, no scale on hover.
4. **Shadows only on floating things**: the composer, dialog, toast, segmented thumb. Always paired with a hairline ring. Cards are flat.
5. **One composer per page.** The main input gets `--radius-composer` (14px), the ring + soft drop, and a 2px `--text-primary` ring on focus.
6. **One solid button per view.** `.primary` is filled with `--text-primary`. Secondary is `.ghost` (ring only). Tertiary is `.icon` (no ring).
7. **Small type.** 14px controls, 16px body, 12–13px meta. Weights 400 / 435 / 520 / 580 (round to 400/500/600 on static fonts). The page title is serif 22px; everything else is the system UI font. Monospace for codes, slugs and keys.
8. **Radius ladder**: 4px badges and kbd, 6–8px controls, 12px cards and toasts, 14px composer.
9. **Focus** is one 2px `--text-primary` ring everywhere. Shadow-drawn rings get a real `outline` under `forced-colors: active`.
10. **Text contrast.** Primary, secondary and muted all pass 4.5:1 on every surface. `--text-faint` is for decorative marks only (underline colour, disabled hints).

## Motion

Motion confirms what just happened and keeps the eye on the same spot. It never decorates.

| Moment | Duration | Easing | Pattern |
|---|---|---|---|
| Press feedback | 60ms (`--dur-fast`) | `--ease` | `:active` sets `transition-duration: var(--dur-fast)`; release eases back at 200ms |
| Row hover | in 60ms, out 200ms | `--ease` | leaves a soft trail when sweeping a list |
| Colour, shadow, opacity | 200ms (`--dur`) | `--ease` | default for any state change |
| Segmented thumb | 140ms (`--dur-slide`) | `--ease` | one `::before` thumb, `translateX(var(--i) * 100%)`, set by `:has(:checked)` |
| Disclosure open | 220ms rows, content 200ms after 30ms | `--ease-out` | `grid-template-rows: 0fr → 1fr`, content fades and drops 4px |
| Disclosure close | 140ms (`--dur-out`) | `--ease-out` | quicker than open, no delay |
| Plus → minus glyph | 200ms | `--ease-out` | vertical bar rotates 90° flat |
| Confirm in place (Copied ✓) | 120–180ms, held 1.2s | `--ease` | `.swap` crossfade, `.icon-swap` scale 0.6 + fade, `.roll` rolls up |
| Row enter / exit | 200ms | `--ease` | height + padding + opacity via WAAPI (`enterRow`, `exitRow`) |
| Row reorder | 200ms | `--ease` | FLIP translateY (`flip`) |
| New / updated item | 1200ms | `--ease` | background starts at +10% and fades out (`flash(el, "fresh")`) |
| Pasted / dropped content | 600ms | `--ease` | same fade on the composer (`flash(el, "pasted")`) |
| Toggle state flip (pin, star) | 150ms | `--ease` | icon scales in from 0.6 (`pop`) |
| Dialog, toast in | 200ms | `--ease` | fade + rise 4px; dialog via `@starting-style`, toast via `.show` |
| Dialog, toast out | 140ms | `--ease` | fade + drop 4px |
| View swap | 200ms | `--ease` | `document.startViewTransition` (`swap`) |
| Busy | 700ms loop | linear | spinner fades in beside the label; the label never changes width |
| Loading | 1.2s loop | ease-in-out | skeleton pulses to 35% opacity |

Rules:

1. **Arrive slower than you leave.** Opening and showing use 200–220ms; closing and hiding use 140ms.
2. **Small distances.** Things move 4px at most when entering or leaving. Only rows (their own height) and thumbs (one cell) travel further.
3. **No animation on page load.** Disclosure transitions sit under `html.ready`, added by `markReady()` after the saved UI state is restored.
4. **Confirm in place.** Copy, save and similar feedback swaps the label or icon inside the same control for 1.2s, with both states in one grid cell so the width never changes. Use a toast only for things that need an action (Undo) or happened off-screen.
5. **Restart, don't stack.** Re-running a one-shot animation goes through `flash()` (remove class, reflow, add).
6. **Leaving elements go inert first.** `exitRow` removes the row from focus and the accessibility tree at once and lets the visual follow.
7. **Toasts queue.** 5s plain, 10s with an action. The timer pauses on hover or focus. Bottom-centre on desktop, top on touch. Announce through one always-present `role="status"` region.
8. **Reduced motion is near-instant, not off.** Durations drop to 1ms so `transitionend` and `animation.finished` still fire. Movement becomes a crossfade, the spinner pulses instead of spinning, and the skeleton stops. JS helpers check `matchMedia("(prefers-reduced-motion: reduce)")` themselves.

## Touch and small screens

- Under `pointer: coarse`, tap targets grow to 44px (`--tap`, `--icon-btn`) and segmented cells get an 8px gap.
- Hover-only reveals (tile actions, keyboard hints) are always visible, or visually hidden, on `hover: none`. Wrap every `:hover` rule in `@media (hover: hover)`.
- Inputs are 16px under 560px so iOS doesn't zoom on focus.
- Respect `env(safe-area-inset-*)` on `main` and the toast.

## Strict CSP

If the app has a strict CSP (`style-src 'self'`), there can be no inline `style=""` attributes. The components are written to need none: the segmented control takes its option count from a class (`.n2`–`.n5`), and every state is a class or attribute toggle. `assets/demo.html` uses inline styles only for demo layout.

## Checklist

- [ ] No colour outside the tokens. No hex gray in components.
- [ ] Only the composer, dialogs, toasts and the segmented thumb have drop shadows.
- [ ] Exactly one `.primary` per view.
- [ ] Every `:hover` is inside `@media (hover: hover)`.
- [ ] Dark mode checked; checkbox tick and on-solid text flip colour.
- [ ] Focus ring visible on every interactive element, including inside clipped panels.
- [ ] Copy-style confirmations don't change the control's width.
- [ ] Nothing animates on first load.
- [ ] With reduced motion on, nothing slides or scales, and every flow still completes.
- [ ] 375px wide: no horizontal scroll, rows stack, tap targets 44px.
