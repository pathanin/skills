---
name: ui-style
description: Manual-only, invoked with /ui-style. Applies my preferred UI style: flat, neutral-gray, hairline borders, black-alpha tints instead of shadows, small type, fast transitions. Tokens, component specs and rules.
disable-model-invocation: true
---

Use this style for any UI built or restyled in this task, unless the project already has a design system; then ask before overriding it. Copy the tokens below into the stylesheet as-is and build components from them. Check the result against the Rules section before finishing.

# Flat / hairline UI style 

## Style in one line
Flat, neutral-gray, low-elevation UI. Layers separated by 1px translucent-black hairlines and
2–5% black tints, not shadows. Colors are pure neutral (no warm tint), text is translucent black.

## Tokens

```css
:root {
  /* Surfaces */
  --bg-page:      #FFFFFF;
  --bg-sidebar:   #FAFAFA;               /* rgb(250,250,250) */
  --bg-raised:    #FFFFFF;               /* composer, segmented thumb */

  /* Interaction tints: black at low alpha, layered on any surface */
  --tint-hover:    rgba(0,0,0,0.05);     /* #0000000d */
  --tint-selected: rgba(0,0,0,0.10);     /* active nav row */
  --tint-track:    rgba(11,11,11,0.05);  /* segmented control track */

  /* Text: translucent black, not gray hex */
  --text-primary:   rgba(0,0,0,0.90);    /* #000000e6 */
  --text-secondary: rgba(0,0,0,0.60);    /* #0009 */
  --text-muted:     rgba(0,0,0,0.47);    /* #0007 */

  /* Borders: hairline */
  --border:        rgba(0,0,0,0.08);     /* #00000014, default */
  --border-strong: rgba(0,0,0,0.10);     /* sidebar right edge */
  --ring-composer: rgba(0,0,0,0.12);     /* #0000001f */

  /* Radius */
  --radius-sm: 4px;  --radius-md: 6px;  --radius: 8px;  --radius-xl: 12px;  --radius-composer: 14px;

  /* Shadows: barely used */
  --shadow-ring:  0 0 0 1px var(--border);                          /* "border" drawn as shadow */
  --shadow-thumb: inset 0 0 0 1px var(--border), 0 1px 2px rgba(0,0,0,0.05);
  --shadow-composer: 0 0 0 1px var(--ring-composer), 0 4px 20px rgba(0,0,0,0.075);
  --shadow-sm: 0 1px 2px rgba(11,11,11,.06), 0 2px 8px rgba(11,11,11,.08);   /* popovers */
  --shadow-panel: 0 0 0 1px var(--border), 0 8px 24px rgba(0,0,0,.12), 0 2px 6px rgba(0,0,0,.08);

  /* Type */
  --font-ui:    system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-serif: Georgia, "Times New Roman", serif;   /* greeting, wordmark */
  --font-mono:  ui-monospace, "SF Mono", Menlo, monospace;
  --text-sm: 14px;  --leading-sm: 20px;   /* all sidebar/control text */
  --text-base: 16px; --leading-base: 24px;
  --weight-body: 400;  --weight-control: 435;  --weight-header: 520;  --weight-semibold: 580;
  /* odd weights (435, 520) need a variable font; with a static font use 400 / 500 */

  /* Motion */
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
  --dur-fast: 60ms;  --dur: 200ms;
}
```

## Components

**Sidebar**: `background: var(--bg-sidebar); border-right: 1px solid var(--border-strong);`
inner padding 12px top, 8px sides, 8px gap between groups. Width 280px.

**Nav row** (New, Search, Projects…)
```css
.nav-row {
  display: flex; align-items: center; gap: 4px;
  height: 32px; padding: 0 2px; border-radius: 8px;
  font: 435 14px/21px var(--font-ui); color: var(--text-primary);
  background: transparent; border: none;
}
.nav-row:hover         { background: var(--tint-hover); }
.nav-row[aria-current] { background: var(--tint-selected); }
.nav-row .icon-slot    { width: 28px; height: 28px; display: grid; place-items: center; }
.nav-row .icon-slot svg{ width: 20px; height: 20px; }
.nav-row kbd           { color: var(--text-secondary); }   /* shortcut hint, right-aligned */
```

**Segmented control** (chat / code toggle)
```css
.segmented { display: inline-flex; height: 28px; padding: 1px; border-radius: 7px;
             background: var(--tint-track); position: relative; }
.segmented .option { width: 34px; border-radius: 5px; background: transparent; }
.segmented .thumb  { position: absolute; top: 1px; bottom: 1px; border-radius: 6px;
                     background: var(--bg-raised); box-shadow: var(--shadow-thumb);
                     transition: transform var(--dur) var(--ease); }  /* slides between options */
```

**Composer / input card**
```css
.composer { background: #fff; border-radius: 14px; padding: 8px; border: none;
            box-shadow: var(--shadow-composer);
            transition: box-shadow var(--dur) var(--ease), background-color var(--dur) var(--ease); }
```

## Rules
1. Neutral grays only. Express every gray as black at an alpha, so it works on any surface.
2. Borders are 1px at 8–12% black. Often drawn as `box-shadow: 0 0 0 1px` so they don't affect layout.
3. Hover = +5% black. Selected = +10% black. No lift, no scale.
4. Shadows only on floating things (composer, popovers, segmented thumb), and always paired with a hairline ring.
5. Small text scale: 14px for all controls, 16px body.
6. Radius ladder: 5–8px for controls, 14px for the composer, 12–16px for cards.
7. Fast transitions: 60ms for press/thumb, 200ms for color/shadow, standard ease.
