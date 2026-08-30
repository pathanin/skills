---
name: dashboard-design
description: >
  Expert dashboard and data-table design principles for product UIs. Trigger when the user is
  building, wireframing, reviewing, or asking for advice on a dashboard, admin panel, data table,
  list view, metrics page, activity feed, or audit log — even if the word "dashboard" is absent.
  Trigger on requests like "review my admin panel", "improve this table", "design a metrics page",
  or "how should I show this data" when the data is records/rows rendered in a product UI.
  Skip when the request is solely about styling an individual chart or graph (axes, palettes,
  mark design — that is charting guidance, not dashboard structure), about backend data modeling
  or APIs, or about non-product surfaces such as spreadsheets, CLI output, documents, or slides.
---

# Dashboard Design

You are applying a set of expert dashboard design principles. These principles distinguish dashboards
that actually work — that users can scan instantly and act on — from dashboards that merely display data.

**Scope boundary:** this skill governs form factor, layout, and interaction design of data-dense UIs.
When a task also involves designing the internals of a chart (axes, color scales, mark types), apply
chart-design guidance for those internals; this skill decides only *whether and where* a chart belongs.

## Step 0: Identify your mode

Before applying any principle, classify the task as exactly one of the following modes. Each mode has
a required output contract. If the user's intent is ambiguous between Review and Build, treat it as
Review — do not redesign something the user only asked you to critique.

**Build** — the user wants a dashboard, table, or data UI created or extended.
Output contract:
1. Design the invisible UI (Principle 3) *before* writing markup or component code: decide empty,
   loading, and error states, hover reveals, and tooltips up front — they affect component structure.
2. The deliverable must include: empty state, loading state, error state, and a tooltip on every
   icon-only control. These are functional requirements, not polish.
3. Before presenting the result, run the Build gate (below). Fix any failed item, or explicitly
   flag it as an open issue. Never silently pass a failed item.

**Review** — the user wants an existing dashboard or data UI critiqued.
Output contract: a numbered list of findings, ordered most severe first. Each finding must:
- be tagged with its governing principle — [P1 data-drives-form], [P2 disclosure], or [P3 invisible-UI];
- name the specific element at fault;
- pair the problem with a concrete fix, not just a judgment.
Cover all three principles; if a principle yields no findings, say so in one line rather than omitting it.

**Advise** — the user asked a question about presenting data in a product UI.
Output contract: a direct recommendation, followed by the governing principle(s) named explicitly and
the reasoning. If two principles pull in different directions, name the tradeoff and state which wins
here and why. Never state a preference without grounding it.

---

## Principle 1: Let the data drive the form

The UI should be shaped by the nature of the data being displayed, not by a generic layout template.

### Table display

- **Chips for bounded-value fields.** If a field has a finite set of possible values (status, department,
  role, category), render it as a chip/badge — not plain text. The constrained set of values is a fact about
  the data; the format should signal it.
- **Right-align numbers.** Digits align by place value, making magnitude comparison instant. Left-aligned or
  center-aligned numbers force the eye to hunt.
- **Truncate long text.** Long strings in table cells crowd out other columns. Truncate with an ellipsis and
  surface the full value on hover or in a detail view.
- **Mute inactive rows.** Rows representing deactivated, archived, or inactive records should be visually
  de-emphasized (lower opacity, lighter text color) so active records dominate attention.

### Choosing the right form factor for time-dimensioned data

If the data has a time or sequential dimension, choose the form by what the reader needs from it:

- **The sequence or the gaps between events are the point** (incident histories, user journeys,
  deployment logs) → render a **timeline**, not a time-sorted table. The timeline can live in a
  sidebar pop-out or as a second column alongside the table; placement is flexible, the form-factor
  change is the point.
- **The aggregate trend is the point** (signup volume, error rates over time) → keep the table and
  add a **summary rollup** — a sparkline or small bar chart above it that surfaces the pattern
  immediately. A raw timestamp column forces the reader to do the work.
- **Both matter** → use both: rollup above, timeline beside or within.

### Color and visual encoding

- Color must come **from the data**, not be applied decoratively. If a row, icon, or chip is red, there
  should be a data-driven reason (urgent status, overdue, error state).
- A **red icon or chip** is justified when the underlying condition is genuinely urgent — it directs the
  eye to what matters. Working threshold: if more than roughly 10% of visible rows are red, nothing reads
  as urgent — tighten the criterion for what earns red rather than letting it inflate.
- An **avatar** outperforms a text name in activity feeds and audit logs where the same actors recur —
  the eye associates who-did-what faster from a face or initials. Keep the name available (adjacent text
  or tooltip) when actors are unfamiliar or the record is compliance-sensitive.

---

## Principle 2: Hide the right things until they're needed (progressive disclosure)

Not everything should be visible at once. Progressive disclosure is the deliberate choice of what to show,
what to surface on interaction, and what to reveal only when explicitly requested.

### The spectrum of explicitness

Think of visibility as a dial:

| Visibility level | Example | When to use |
|---|---|---|
| Always visible, labeled | "Share" button in the toolbar | High-importance, frequently used |
| Always visible, icon-only | Filter icon in table header | Medium-importance, space-constrained |
| Revealed on hover | Copy icon on a cell | Low-importance, would add visual noise |
| Revealed on click/tap | Remove user in a popover | Destructive or secondary action |

Place each action on this spectrum by three factors: **action importance × usage frequency × available
space**. Lower importance, lower frequency, and tighter space each push the action toward later reveal.
A frequent action stays visible even when its importance is modest; a rare action hides even when space
is plentiful.

### Popovers over navigation

Infrequent actions (share, export, manage members) should open a **popover** anchored to the triggering
element — not navigate to a separate page. This preserves context and avoids round-trip friction. Inside
the popover: put the primary action (search box, main input) immediately visible at the top; put secondary
or destructive actions (remove, delete) behind a hover reveal with a tooltip.

### Onboarding is progressive disclosure for first use

- Start with a **single tooltip** on the most important action. One call to action.
- After the user completes it, introduce the next step — a second tooltip or a corner checklist.
- Goal: sequence the feature revelation, never front-load it.
- Anti-pattern: a modal at login listing six features. It gets dismissed and forgotten.

---

## Principle 3: Build the invisible UI

A finished dashboard is defined as much by what you can't immediately see as by what you can. This is the
dimension that most clearly separates experienced from inexperienced dashboard work — which is why in
Build mode it is designed first, not last.

### What "invisible UI" means

These are UI elements and states that are not visible in the default view but are essential for the
dashboard to actually function:

- **Copy chips** that appear when hovering over a cell value
- **Comment indicators** — a small triangle or dot in a cell corner that signals a thread exists
- **Inline edit mode** triggered by clicking a cell
- **Row action menus** revealed on hover
- **Bulk selection** revealed when a checkbox column appears on row hover
- **Empty states** — what the table looks like when there's no data
- **Error states** — what happens when a data fetch fails
- **Loading skeletons** — the placeholder before data arrives

In a well-built dashboard, the hidden states typically outnumber the visible ones. They are not optional
polish. Without them, the table doesn't function.

### Modals, drawers, and panels

New features rarely need a dedicated page. Instead, ask:
- Can this live in a **slide-out drawer** triggered from a table row?
- Can this be a **modal** launched from an action button?
- Can this be embedded in an **expandable row**?

Designing the hidden states of drawers and modals — their loading states, their empty states, their error
states — is as important as designing their default visible state.

### Tooltips are mandatory, not optional

Assume users won't understand every icon. Assume they may want more context on an ambiguous label. Every
icon-only button needs a tooltip. Every truncated value needs a hover expansion. Every status chip whose
meaning isn't obvious needs a tooltip definition.

The absence of tooltips is the primary tell of an inexperienced dashboard build.

### Rarely-seen moments still count

- First-time onboarding (the dashboard before any data exists)
- Feature announcement banners
- Upgrade prompts
- Permission-denied states

These are UI. Design them.

---

## The Build gate

In Build mode, run this checklist before presenting the deliverable. Every item must be either satisfied
or explicitly flagged as an open issue in your output — a silent pass is a failure of the skill.

1. Does every table column use the right format for its data type (chips for bounded values,
   right-aligned numbers, truncated long text, avatars where actors recur)?
2. Is time-dimensioned data rendered per the form-factor rule (timeline for sequence, rollup for trend)?
3. Is every color data-driven, with red held under the urgency threshold?
4. Is every action placed on the explicitness spectrum by importance × frequency × space?
5. Do infrequent actions use popovers/drawers/modals instead of page navigation?
6. Are the empty, loading, and error states designed and present in the deliverable?
7. Does every icon-only control, truncated value, and non-obvious status chip have a tooltip?
