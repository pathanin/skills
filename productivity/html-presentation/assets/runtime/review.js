// Review mode: only when the deck is served by the html-presentation review server (http://127.0.0.1:8765/).
// Opened as a plain file (presenting, screenshots, PDF) this script does nothing.
//   E  edit text in place        C  drop a comment (click where it applies)        H  hide pins
// Everything autosaves to review.json next to index.html. Claude applies the edits and answers comments.
// Labels follow <html lang>: Thai for "th", English otherwise.
(function () {
  if (!/^https?:$/.test(location.protocol)) return;
  const API = "/api/review";
  const TH = (document.documentElement.lang || "").toLowerCase().startsWith("th");
  const L = TH ? { edit: "แก้ข้อความ (E)", cmt: "คอมเมนต์ (C)", hide: "ซ่อนหมุด (H)", saving: "กำลังบันทึก…", saved: "บันทึกแล้ว ",
      fail: "บันทึกไม่สำเร็จ", down: "บันทึกไม่สำเร็จ (ปิดเซิร์ฟเวอร์อยู่?)", slide: "สไลด์ ", fixed: " · แก้แล้ว", ph: "พิมพ์คอมเมนต์…",
      del: "ลบ", cancel: "ยกเลิก", ok: "บันทึก", stat: (n, o) => `แก้ ${n} · คอมเมนต์ค้าง ${o}`, nosrv: "ต่อเซิร์ฟเวอร์ไม่ได้", loc: "th-TH" }
    : { edit: "Edit text (E)", cmt: "Comment (C)", hide: "Hide pins (H)", saving: "Saving…", saved: "Saved ",
      fail: "Save failed", down: "Save failed (server stopped?)", slide: "Slide ", fixed: " · done", ph: "Type a comment…",
      del: "Delete", cancel: "Cancel", ok: "Save", stat: (n, o) => `${n} edits · ${o} open comments`, nosrv: "Cannot reach the review server", loc: undefined };
  let data = { edits: {}, comments: [] }, mode = "", saveTimer = 0;
  const slides = [...document.querySelectorAll(".slide")];
  const slideOf = (el) => el.closest(".slide");
  const num = (sl) => slides.indexOf(sl) + 1;

  // a stable key per text box: slide id + PowerPoint shape name (+ cell index for tables)
  function keyOf(tx) {
    const sl = slideOf(tx), host = tx.closest("[data-name]");
    let k = sl.id + "|" + host.dataset.name;
    if (tx.classList.contains("cell")) k += "#" + [...host.querySelectorAll(".cell")].indexOf(tx);
    return k;
  }
  const texts = () => document.querySelectorAll(".slide .tx, .slide .cell");
  const plain = (el) => el.innerText.replace(/ /g, " ").trim();

  // ---------- UI ----------
  const css = document.createElement("style");
  css.textContent = `
  #rv{position:fixed;left:12px;bottom:10px;z-index:50;display:flex;gap:6px;align-items:center;font:13px/1 "DeckFont",sans-serif;user-select:none}
  #rv button{font:inherit;padding:7px 11px;border-radius:8px;border:1px solid #3a4470;background:#1a2147;color:#dfe5ff;cursor:pointer}
  #rv button.on{background:#F5B400;border-color:#F5B400;color:#1a1300;font-weight:700}
  #rv .st{color:#9aa3c7;margin-left:4px}
  body.rv-edit .slide .tx,body.rv-edit .slide .cell{outline:1px dashed rgba(245,180,0,.55);outline-offset:-1px;cursor:text}
  body.rv-edit .slide .tx:focus,body.rv-edit .slide .cell:focus{outline:2px solid #F5B400;background:rgba(255,248,214,.35)}
  .rv-changed{box-shadow:inset 0 0 0 2px rgba(245,180,0,.9)}
  body.rv-edit .slide,body.rv-cmt .slide{cursor:crosshair}
  body.rv-edit .slide{cursor:default}
  body.rv-edit .pic.vid,body.rv-cmt .pic.vid{pointer-events:none}
  .rv-pin{position:absolute;z-index:40;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50% 50% 50% 4px;background:#F5B400;color:#1a1300;
    font:700 13px/26px "DeckFont",sans-serif;text-align:center;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.35)}
  .rv-pin.done{background:#9aa3c7;color:#fff}
  .rv-pin.reply::after{content:"";position:absolute;right:-3px;top:-3px;width:9px;height:9px;border-radius:50%;background:#1449F0;border:2px solid #fff}
  body.rv-hide .rv-pin{display:none}
  .rv-pop{position:absolute;z-index:45;width:300px;background:#fff;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.35);padding:10px;font:14px/1.5 "DeckFont",sans-serif;color:#0D1230}
  .rv-pop textarea{width:100%;height:84px;font:inherit;border:1px solid #cfd6ea;border-radius:6px;padding:6px;resize:vertical}
  .rv-pop .who{font-size:12px;color:#4D5675;margin-bottom:4px}
  .rv-pop .rep{background:#EEF3FF;border-radius:6px;padding:6px 8px;margin:6px 0;font-size:13px}
  .rv-pop .bt{display:flex;gap:6px;justify-content:flex-end;margin-top:6px}
  .rv-pop button{font:inherit;font-size:13px;padding:5px 10px;border-radius:6px;border:1px solid #cfd6ea;background:#fff;cursor:pointer}
  .rv-pop button.pri{background:#1449F0;border-color:#1449F0;color:#fff}`;
  document.head.appendChild(css);
  const bar = document.createElement("div"); bar.id = "rv";
  bar.innerHTML = `<button data-m="edit" title="E">${L.edit}</button><button data-m="cmt" title="C">${L.cmt}</button>` +
    `<button data-m="hide" title="H">${L.hide}</button><span class="st"></span>`;
  document.body.appendChild(bar);
  const status = bar.querySelector(".st");
  bar.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) toggle(b.dataset.m); });

  function toggle(m) {
    if (m === "hide") { document.body.classList.toggle("rv-hide"); bar.querySelector('[data-m="hide"]').classList.toggle("on"); return; }
    mode = mode === m ? "" : m;
    document.body.classList.toggle("rv-edit", mode === "edit");
    document.body.classList.toggle("rv-cmt", mode === "cmt");
    bar.querySelectorAll('[data-m="edit"],[data-m="cmt"]').forEach((b) => b.classList.toggle("on", b.dataset.m === mode));
    texts().forEach((t) => { if (mode === "edit") t.setAttribute("contenteditable", "plaintext-only"); else t.removeAttribute("contenteditable"); });
    // bullet glyphs are paragraph formatting: keep typed text out of them (the export drops .bu spans)
    document.querySelectorAll(".slide .bu").forEach((b) => { if (mode === "edit") b.setAttribute("contenteditable", "false"); else b.removeAttribute("contenteditable"); });
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    closePop();
  }
  document.addEventListener("keydown", (e) => {
    if (isTyping(e.target)) { if (e.key === "Escape" && e.target.isContentEditable) e.target.blur(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === "e") toggle("edit"); else if (k === "c") toggle("cmt"); else if (k === "h") toggle("hide");
    else if (k === "escape") { closePop(); if (mode) toggle(mode); }
  }, true);
  function isTyping(t) { return t && (t.isContentEditable || /^(TEXTAREA|INPUT)$/.test(t.tagName)); }
  // deck.js navigation must ignore keys while typing
  ["keydown"].forEach((ev) => document.addEventListener(ev, (e) => { if (isTyping(e.target) && e.key !== "Escape") e.stopImmediatePropagation(); }, true));

  // ---------- save ----------
  function save() {
    clearTimeout(saveTimer); status.textContent = L.saving;
    saveTimer = setTimeout(async () => {
      try {
        const r = await fetch(API, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
        status.textContent = r.ok ? L.saved + new Date().toLocaleTimeString(L.loc, { hour: "2-digit", minute: "2-digit" }) : L.fail;
      } catch { status.textContent = L.down; }
    }, 400);
  }

  // ---------- text edits ----------
  const original = new Map();
  texts().forEach((t) => original.set(t, { text: plain(t), html: t.innerHTML }));
  function applySaved() {
    texts().forEach((t) => {
      const e = data.edits[keyOf(t)];
      if (!e) return;
      if (e.before === original.get(t).text) { t.innerHTML = e.html; t.classList.add("rv-changed"); }
      else if (e.after === original.get(t).text) { delete data.edits[keyOf(t)]; }   // already applied to index.html
    });
  }
  document.addEventListener("focusout", (e) => {
    const t = e.target; if (!t.classList || !(t.classList.contains("tx") || t.classList.contains("cell")) || !original.has(t)) return;
    const k = keyOf(t), o = original.get(t), now = plain(t);
    if (now === o.text) { if (data.edits[k]) { delete data.edits[k]; t.innerHTML = o.html; t.classList.remove("rv-changed"); save(); } return; }
    data.edits[k] = { slide: num(slideOf(t)), name: t.closest("[data-name]").dataset.name, before: o.text, after: now, html: t.innerHTML, at: new Date().toISOString() };
    t.classList.add("rv-changed"); save();
  });

  // ---------- comments ----------
  let pop = null;
  function closePop() { if (pop) { pop.remove(); pop = null; } }
  function stagePoint(sl, ev) { const r = sl.getBoundingClientRect(), s = r.width / 1280; return { x: (ev.clientX - r.left) / s, y: (ev.clientY - r.top) / s }; }
  function drawPins() {
    document.querySelectorAll(".rv-pin").forEach((p) => p.remove());
    data.comments.forEach((c, k) => {
      const sl = document.getElementById("s" + c.slide); if (!sl) return;
      const p = document.createElement("div");
      p.className = "rv-pin" + (c.done ? " done" : "") + (c.reply ? " reply" : "");
      p.textContent = k + 1; p.style.left = c.x + "px"; p.style.top = c.y + "px"; p.title = c.text;
      p.addEventListener("click", (e) => { e.stopPropagation(); openPop(sl, c); });
      sl.appendChild(p);
    });
  }
  function openPop(sl, c) {
    closePop(); pop = document.createElement("div"); pop.className = "rv-pop";
    pop.style.left = Math.min(c.x + 16, 1280 - 312) + "px"; pop.style.top = Math.min(c.y + 10, 720 - 200) + "px";
    const esc = (s) => String(s).replace(/[&<>"]/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
    pop.innerHTML = `<div class="who">${L.slide}${c.slide}${c.name ? " · " + esc(c.name) : ""}${c.done ? L.fixed : ""}</div>` +
      (c.reply ? `<div class="rep"><b>Claude:</b> ${esc(c.reply)}</div>` : "") +
      `<textarea placeholder="${L.ph}">${esc(c.text || "")}</textarea>` +
      `<div class="bt">${data.comments.includes(c) ? `<button data-a="del">${L.del}</button>` : ""}<button data-a="x">${L.cancel}</button><button class="pri" data-a="ok">${L.ok}</button></div>`;
    sl.appendChild(pop);
    const ta = pop.querySelector("textarea"); ta.focus();
    ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) pop.querySelector('[data-a="ok"]').click(); if (e.key === "Escape") closePop(); });
    pop.addEventListener("click", (e) => {
      e.stopPropagation(); const a = e.target.dataset.a; if (!a) return;
      if (a === "ok" && ta.value.trim()) {
        if (c.text !== ta.value.trim()) { c.text = ta.value.trim(); c.done = false; c.at = new Date().toISOString(); }
        if (!data.comments.includes(c)) data.comments.push(c);
        save();
      } else if (a === "del") { data.comments.splice(data.comments.indexOf(c), 1); save(); }
      closePop(); drawPins();
    });
  }
  document.addEventListener("click", (e) => {
    if (mode !== "cmt" || pop && pop.contains(e.target) || e.target.closest("#rv")) return;
    const sl = e.target.closest(".slide"); if (!sl) return;
    e.preventDefault(); e.stopPropagation();
    const pt = stagePoint(sl, e);
    // which shape is under the click (smallest box wins)
    let name = "";
    let best = 1e12;
    sl.querySelectorAll("[data-name]").forEach((el) => { const r = el.getBoundingClientRect();
      if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom && r.width * r.height < best && r.width < sl.getBoundingClientRect().width * 0.95) { best = r.width * r.height; name = el.dataset.name; } });
    openPop(sl, { slide: num(sl), name, x: Math.round(pt.x), y: Math.round(pt.y), text: "" });
  }, true);

  fetch(API, { cache: "no-store" }).then((r) => r.json()).then((d) => {
    data = { edits: d.edits || {}, comments: d.comments || [] };
    applySaved(); drawPins();
    const open = data.comments.filter((c) => !c.done).length, n = Object.keys(data.edits).length;
    status.textContent = L.stat(n, open);
  }).catch(() => { status.textContent = L.nosrv; });
})();
