# Implementation patterns

Event-level recipes for the ladder in SKILL.md. Framework-neutral TypeScript/DOM sketches; adapt to
the project's stack and its existing event utilities rather than pasting verbatim.

## Contents

1. Click vs double-click (L1 and L2)
2. Submenu aim (L3)
3. Tooltip warm mode (L3)
4. Drag reorder with edge autoscroll (L3)
5. Act-first delete with undo and deferred commit (L4)
6. Optimistic update with visible rollback (L4)
7. Press/release semantics (L5)
8. Threshold gesture with preview (L5)

---

## 1. Click vs double-click

**Try L1 first.** If single-click can become "select" and double-click "open/edit", no timer is
needed — handle `click` (select) and `dblclick` (edit) independently; `dblclick` fires after two
`click`s, and selecting twice is harmless.

**L2 when they truly compete** (single-click navigates away, double-click edits in place):

```ts
const DOUBLE_CLICK_MS = 500; // browsers don't expose the OS setting; native apps should read it
let pending: number | undefined;

row.addEventListener('click', (e) => {
  row.classList.add('is-pressed');          // instant acknowledgement, not the action
  if (e.detail > 1) return;                 // second click of a pair: dblclick handles it
  pending = window.setTimeout(() => {
    row.classList.remove('is-pressed');
    openDetail(row.dataset.id);
  }, DOUBLE_CLICK_MS);
});

row.addEventListener('dblclick', () => {
  window.clearTimeout(pending);
  row.classList.remove('is-pressed');
  startInlineRename(row);
});

row.addEventListener('keydown', (e) => {   // keyboard path: no ambiguity, no wait
  if (e.key === 'Enter') openDetail(row.dataset.id);
  if (e.key === 'F2') startInlineRename(row);
});
```

Also add a visible "Rename" item to the row's menu — double-click must not be the only way in.
Native platforms: read the system interval (`GetDoubleClickTime()` on Windows,
`NSEvent.doubleClickInterval` on macOS) instead of a constant.

## 2. Submenu aim

Keep the last few pointer positions. When the pointer enters a sibling row while a submenu is open,
check whether it is moving toward the submenu:

```ts
// Submenu opens to the right. a = previous point, b = current point.
// The pointer is "aiming" if, from a to b, the slope to the submenu's top-near corner
// decreased and the slope to its bottom-near corner increased (it is inside the
// narrowing triangle). Add a tolerance in px above/below the submenu to forgive curves.
function isAiming(a: Pt, b: Pt, top: Pt, bottom: Pt): boolean {
  const slope = (p: Pt, q: Pt) => (q.y - p.y) / (q.x - p.x);
  return slope(b, top) < slope(a, top) && slope(b, bottom) > slope(a, bottom);
}
```

- Aiming → defer switching and re-check after ~300 ms. If the pointer has not moved since the last
  check, switch to the hovered row (the user paused on it; they meant it).
- Not aiming, or pointer came from outside the menu → switch immediately. No fixed hover delay.
- Touch: open submenus on tap. Keyboard: Right/Left arrows open and close, per the WAI-ARIA menu pattern.

Reference implementation: `kamens/jQuery-menu-aim` (3 tracked positions, 75 px tolerance, 300 ms
re-check). Many modern menu libraries implement a "safe triangle" or "safe polygon" equivalent;
use the project's library if it has one.

## 3. Tooltip warm mode

```ts
const INITIAL = 500, RESHOW = 100, COOL_DOWN = 800;
let warmUntil = 0;
function delayFor(now: number) { return now < warmUntil ? RESHOW : INITIAL; }
function onTooltipHidden(now: number) { warmUntil = now + COOL_DOWN; }
```

Show on keyboard focus as well as hover; dismiss on Escape without moving focus (WCAG 1.4.13).

## 4. Drag reorder with edge autoscroll

- Open a gap at the computed insertion index on every move (animate neighbours with transform),
  so the list already shows the result before release. Prefer the gap to a thin line or a position
  label, which the user has to translate.
- Autoscroll zone of ~48–80 px at each edge of the scroll container. Speed is a ramp, not a switch:

```ts
function scrollSpeed(distanceFromEdge: number, zone = 64, max = 20): number {
  if (distanceFromEdge >= zone) return 0;
  const t = 1 - distanceFromEdge / zone;   // 0 at zone boundary, 1 at the edge
  return max * t * t;                      // ease-in: gentle near the boundary
}
```

- Escape, or dropping outside a valid target, returns the item to its origin.
- Provide a non-drag path (Move up / Move down menu items) — WCAG 2.5.7 — and keyboard reordering
  with the standard keys: Space picks up, arrows move, Space drops, Escape cancels, each step
  announced in a live region.

## 5. Act-first delete with undo and deferred commit

```ts
async function deleteTask(id: string) {
  hideLocally(id);                                    // UI reflects intent at once
  const timer = setTimeout(() => commitDelete(id), UNDO_MS); // the server call waits
  showToast({
    message: 'Task deleted',
    action: { label: 'Undo', run: () => { clearTimeout(timer); restoreLocally(id); } },
    durationMs: UNDO_MS,            // pause the countdown while hovered/focused
  });
}
```

- `UNDO_MS` of 5–10 s for the toast. Also flush pending commits on page unload (or commit as a soft
  delete immediately and hard-delete later, which survives a closed tab).
- Better still for user content: soft delete (`deleted_at`) on the server right away, a "Recently
  deleted" view, and a purge job after N days. The toast then calls an undelete endpoint.
- Wire the platform undo shortcut (Cmd/Ctrl+Z) to the same restore.
- The toast must be reachable by keyboard and announced to screen readers (`role="status"`).

## 6. Optimistic update with visible rollback

```ts
async function toggleDone(task: Task) {
  const prev = task.done;
  setDone(task.id, !prev);                       // optimistic
  try {
    await api.update(task.id, { done: !prev });
  } catch {
    setDone(task.id, prev);                      // roll back...
    showToast({ message: "Couldn't save — change undone", action: retry });  // ...and say so
  }
}
```

Guard against out-of-order responses (request IDs or versioning) when the same item can be changed
twice quickly. Don't use optimistic commits for payments, sending to other people, or permission
changes — show a pending state and wait for confirmation.

## 7. Press/release semantics

- Action buttons: act on `click` (which fires on release, only if press and release land on the same
  element). Don't trigger the action on `pointerdown`/`mousedown`.
- Menu buttons: open on `pointerdown`, track the pointer, and choose the item under the pointer on
  `pointerup` if the pointer moved into the menu; if the user released on the button itself, leave the
  menu open for click-to-choose. Both styles must work.
- Hold interactions: commit on release, cancel on Escape or `pointercancel`.

## 8. Threshold gesture with preview

- Map gesture distance to a progress value 0…1 and render it continuously (the row slides and the
  delete affordance grows; the refresh spinner fills).
- Cross the threshold → change the preview to its committed look (color, icon, a light haptic on
  mobile) *before* release, so the user knows letting go will act.
- Move back under the threshold → revert the preview; releasing then does nothing.
- Commit on release only. Offer the same action in a visible menu.
