// Screenshot / QA DECK/index.html with ONE headless Edge (or Chrome) driven over the DevTools protocol.
// No npm packages: uses Node's built-in WebSocket and fetch (Node 22+).
//   node shoot.mjs DECK OUTDIR [1,5,9]   -> OUTDIR/sNN.png (1280x720)
//   node shoot.mjs DECK --qa             -> text overflow + font check, all slides
//   node shoot.mjs DECK --video          -> every clip loads and plays
//   node shoot.mjs DECK --pdf FILE       -> print the deck to PDF (one slide per page)
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [DECK, ...ARGS] = process.argv.slice(2);
if (!DECK || !existsSync(join(DECK, "index.html"))) { console.error("usage: node shoot.mjs DECK (OUTDIR [1,2] | --qa | --video | --pdf FILE)"); process.exit(2); }
const INDEX = pathToFileURL(resolve(DECK, "index.html")).href;
const PF = [process.env["ProgramFiles(x86)"], process.env.ProgramFiles, process.env.LOCALAPPDATA].filter(Boolean);
const CANDIDATES = [process.env.BROWSER,
  ...PF.map((p) => join(p, "Microsoft", "Edge", "Application", "msedge.exe")),
  ...PF.map((p) => join(p, "Google", "Chrome", "Application", "chrome.exe")),
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium", join(process.env.HOME || "", "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
  "/usr/bin/microsoft-edge", "/usr/bin/google-chrome", "/usr/bin/chromium"].filter(Boolean);
const EDGE = CANDIDATES.find((p) => existsSync(p));
if (!EDGE) { console.error("no Edge/Chrome found; set BROWSER to the browser's path"); process.exit(2); }
const PORT = 9333 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), "deckshot-"));
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run",
  "--disable-extensions", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--allow-file-access-from-files",
  // macOS: keep headless Chrome away from the login Keychain (otherwise it can ask for access)
  ...(process.platform === "darwin" ? ["--use-mock-keychain", "--password-store=basic"] : []), "about:blank"], { stdio: "ignore" });
// Ctrl+C or a crash must not leave a headless browser and its temp profile behind
const bail = () => {
  const rm = () => { try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }); } catch { } process.exit(130); };
  if (edge.exitCode !== null || edge.signalCode) return rm();
  edge.once("exit", rm); setTimeout(rm, 2000);
  try { edge.kill("SIGKILL"); } catch { }
};
process.once("SIGINT", bail); process.once("SIGTERM", bail);
process.once("exit", () => { try { edge.kill("SIGKILL"); } catch { } });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, seq = 0;
const pending = new Map();
const events = [];
function send(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((res, rej) => pending.set(id, { res, rej }));
}
async function connect() {
  for (let k = 0; k < 50; k++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) { ws = new WebSocket(page.webSocketDebuggerUrl); break; }
    } catch { }
    await sleep(200);
  }
  if (!ws) throw new Error("could not reach the browser's DevTools");
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  ws.addEventListener("message", (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id); pending.delete(msg.id);
      msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
    } else if (msg.method) events.push(msg);
  });
}
async function evaluate(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
  return r.result.value;
}
async function load(url) {
  await send("Page.navigate", { url });
  for (let k = 0; k < 100; k++) {
    if (await evaluate("document.readyState==='complete'").catch(() => false)) break;
    await sleep(100);
  }
  await evaluate("document.fonts.ready.then(()=>true)");
}
async function imagesReady(sel = ".slide.on img") {
  await evaluate(`Promise.all([...document.querySelectorAll('${sel}')].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r})))`);
}

try {
  await connect();
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  const args = ARGS;
  if (args[0] === "--qa") {
    await load(INDEX + "?qa");
    for (let k = 0; k < 100 && !(await evaluate("document.getElementById('qa').dataset.done==='1'")); k++) await sleep(100);
    console.log((await evaluate("document.getElementById('qa').textContent")) || "(no issues)");
    const svgBox = await evaluate(`[...document.querySelectorAll('.slide')].flatMap((s,k)=>[...s.querySelectorAll('[data-prst]')]
      .filter(e=>!['line','triangle','rightArrow','leftArrow','chevron','homePlate','custom','star4','star5','star6','star8','diamond','parallelogram'].includes(e.dataset.prst)).map(e=>'s'+(k+1)+' ['+(e.dataset.name||'master')+'] preset '+e.dataset.prst+' drawn as its bounding box'))`);
    if (svgBox.length) console.log(svgBox.join("\n"));
  } else if (args[0] === "--video") {
    await load(INDEX + "?flat");
    const res = await evaluate(`(async()=>{const out=[];for(const v of document.querySelectorAll('video')){
      v.muted=true; v.preload='auto'; v.load();
      await new Promise(r=>{v.onloadedmetadata=r;v.onerror=r;setTimeout(r,8000)});
      let t0=v.currentTime; try{await v.play();}catch(e){}
      await new Promise(r=>setTimeout(r,1000)); const ok=v.currentTime>t0; v.pause();
      out.push((ok?'ok  ':'FAIL')+' '+v.getAttribute('src')+' '+(v.duration||0).toFixed(1)+'s '+(v.videoWidth+'x'+v.videoHeight));}
      return out.join('\\n')||'(no clips)';})()`);
    console.log(res);
  } else if (args[0] === "--pdf") {
    await load(INDEX + "?flat");
    await imagesReady("img");
    const r = await send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true, marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 });
    writeFileSync(args[1], Buffer.from(r.data, "base64"));
    console.log("pdf", args[1]);
  } else {
    const out = args[0]; mkdirSync(out, { recursive: true });
    await load(INDEX + "?shot#1");
    const n = await evaluate("document.querySelectorAll('.slide').length");
    const nums = args[1] ? args[1].split(",").map(Number) : Array.from({ length: n }, (_, k) => k + 1);
    for (const s of nums) {
      await evaluate(`location.hash='#${s}'`);
      await sleep(60);
      await imagesReady();
      const r = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: 1280, height: 720, scale: 1 } });
      writeFileSync(join(out, `s${String(s).padStart(2, "0")}.png`), Buffer.from(r.data, "base64"));
    }
    console.log("shot", nums.length);
  }
} finally {
  try { ws && ws.close(); } catch { }
  const gone = new Promise((r) => edge.exitCode !== null ? r() : edge.once("exit", r));
  edge.kill();
  await Promise.race([gone, sleep(2000)]);
  try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch { }
}
