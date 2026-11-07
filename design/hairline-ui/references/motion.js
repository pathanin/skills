// hairline-ui motion helpers. Plain browser JS, no dependencies. Copy what you need.
// Every helper respects prefers-reduced-motion and degrades to an instant change where an API is missing.

const EASE = "cubic-bezier(0.4, 0, 0.2, 1)";
const RM = matchMedia("(prefers-reduced-motion: reduce)");

// 1. No animation on page load. CSS transitions for disclosures are scoped under html.ready;
//    add it two frames after the saved UI state is restored, so restored-open panels don't animate open.
function markReady() {
  requestAnimationFrame(() => requestAnimationFrame(() => document.documentElement.classList.add("ready")));
}

// 2. Restart a one-shot CSS animation (.fresh row highlight, .pasted composer flash).
//    Removing and re-adding the class alone does nothing; the reflow in between restarts it.
function flash(el, cls) {
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
  el.addEventListener("animationend", () => el.classList.remove(cls), { once: true });
}

// 3. Confirm in place (.swap, .icon-swap, .roll): add .done, take it off after 1.2s.
//    Repeated clicks extend the confirmation instead of flickering it.
function confirmDone(el, ms = 1200) {
  el.classList.add("done");
  clearTimeout(el._doneTimer);
  el._doneTimer = setTimeout(() => el.classList.remove("done"), ms);
}

// 4. Disclosure: button with aria-expanded + .reveal panel. Closed panels are inert so Tab skips them.
function setReveal(button, panel, open) {
  button.setAttribute("aria-expanded", open ? "true" : "false");
  panel.classList.toggle("open", open);
  panel.inert = !open;
}

// 5. Swap one view for another (form -> result, list -> detail) with a crossfade.
//    Instant with reduced motion, unsupported browsers or a hidden tab.
function swap(fn) {
  if (!document.startViewTransition || RM.matches || document.hidden) { fn(); return; }
  try { document.startViewTransition(fn); } catch { fn(); }
}

// 6. Rows grow in and collapse out (height + padding + opacity, 200ms) so the list never jumps.
function enterRow(li) {
  if (RM.matches || !li.animate) return;
  const h = li.offsetHeight;
  li.style.overflow = "hidden";
  const a = li.animate([{ height: "0px", opacity: 0, paddingTop: "0px", paddingBottom: "0px" }, { height: h + "px", opacity: 1 }],
    { duration: 200, easing: EASE });
  a.finished.then(() => { li.style.overflow = ""; }, () => { li.style.overflow = ""; });
}
function exitRow(li) {
  // Leaving rows stop taking input and leave the accessibility tree at once; the visual follows.
  li.classList.add("leaving");
  li.setAttribute("aria-hidden", "true");
  li.removeAttribute("tabindex");
  if (RM.matches || !li.animate || !li.isConnected) { li.remove(); return; }
  li.style.overflow = "hidden";
  const a = li.animate([{ height: li.offsetHeight + "px", opacity: 1 }, { height: "0px", opacity: 0, paddingTop: "0px", paddingBottom: "0px" }],
    { duration: 200, easing: EASE, fill: "forwards" });
  a.finished.then(() => li.remove(), () => li.remove());
}

// 7. FLIP reorder: rows glide to their new place (pin/unpin, sort). Call measure() before the DOM change, play() after.
function flip(rows) {
  const before = new Map();
  if (!RM.matches) for (const r of rows) if (r.isConnected) before.set(r, r.getBoundingClientRect().top);
  return function play() {
    for (const [r, top] of before) {
      if (!r.isConnected || !r.animate) continue;
      const dy = top - r.getBoundingClientRect().top;
      if (Math.abs(dy) >= 1) r.animate([{ transform: "translateY(" + dy + "px)" }, { transform: "translateY(0)" }], { duration: 200, easing: EASE });
    }
  };
}
// usage: const play = flip([...list.children]); reorderDom(); play();

// 8. Toggle pop: an icon whose state flips (pin, star) scales in from 0.6. Reduced motion: fade only. Not on first render.
function pop(el) {
  if (!el.animate) return;
  if (RM.matches) el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, easing: EASE });
  else el.animate([{ transform: "scale(0.6)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }], { duration: 150, easing: EASE });
}

// 9. Toasts queue instead of replacing each other. 5s plain, 10s with an action (Undo).
//    The timer pauses while the toast is hovered or focused and resumes with at least 3s left.
//    Markup: <div id="toast" class="toast"><span class="toast-text"></span><button type="button" class="toast-action" hidden></button></div>
//    plus one always-present <div id="status" class="sr-only" role="status" aria-live="polite"></div>.
const toasts = { queue: [], cur: null, timer: 0, left: 0, started: 0, hover: false, focus: false };
function announce(text) {
  const s = document.getElementById("status");
  s.textContent = "";
  setTimeout(() => { s.textContent = text; }, 60); // clear-then-set so repeats are read again
}
function toast(text, action) {
  toasts.queue.push({ text, action, ms: action ? 10000 : 5000 });
  if (!toasts.cur) nextToast();
}
function nextToast() {
  const t = document.getElementById("toast"), btn = t.querySelector(".toast-action");
  const item = toasts.queue.shift() || null;
  toasts.cur = item;
  if (!item) return;
  t.querySelector(".toast-text").textContent = item.text;
  btn.textContent = item.action ? item.action.label : "";
  btn.hidden = !item.action;
  btn.onclick = item.action ? () => { dismissToast(); item.action.run(); } : null;
  t.classList.toggle("has-action", !!item.action);
  t.classList.add("show");
  announce(item.text);
  toasts.left = item.ms;
  runToastTimer();
}
function runToastTimer() {
  clearTimeout(toasts.timer);
  if (!toasts.cur || toasts.hover || toasts.focus) return;
  toasts.started = Date.now();
  toasts.timer = setTimeout(dismissToast, toasts.left);
}
function holdToast(key, on) {
  const was = toasts.hover || toasts.focus;
  toasts[key] = on;
  const is = toasts.hover || toasts.focus;
  if (was === is || !toasts.cur) return;
  if (is) { clearTimeout(toasts.timer); toasts.left = Math.max(3000, toasts.left - (Date.now() - toasts.started)); }
  else runToastTimer();
}
function dismissToast() {
  clearTimeout(toasts.timer);
  if (!toasts.cur) return;
  toasts.cur = null; toasts.focus = false;
  document.getElementById("toast").classList.remove("show");
  if (toasts.queue.length) setTimeout(nextToast, 160); // let the exit finish before the next one rises
}
function wireToast() {
  const t = document.getElementById("toast");
  t.addEventListener("pointerenter", () => holdToast("hover", true));
  t.addEventListener("pointerleave", () => holdToast("hover", false));
  t.addEventListener("focusin", () => holdToast("focus", true));
  t.addEventListener("focusout", () => holdToast("focus", false));
}
