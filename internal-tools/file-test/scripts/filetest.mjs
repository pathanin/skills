#!/usr/bin/env node
// filetest: load a local HTML file over file:// in a real browser and report
// everything that breaks, including failures the page silently swallows.
import { parseArgs } from 'node:util';
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HAZARD_SCRIPT = readFileSync(path.join(ROOT, 'scripts/hazards.js'), 'utf8');
const HAZARD_MARK = '[filetest-hazard]';

const USAGE = `Usage: filetest <page.html | file:///...> [options]

Loads the page over file:// in a real browser and reports page errors, console
errors, failed requests and file://-specific hazards (blocked fetch/modules/
workers, tainted canvas, dropped cookies, ...). Exit code 0 = clean, 1 = issues
found, 2 = tool error.

Options:
  --browser <name>     chrome (default, your installed Chrome) | chromium | firefox | webkit
  --viewport <WxH>     viewport size, default 1280x800
  --wait <ms>          settle time after the load event, default 500
  --screenshot <path>  save a full-page PNG after load (and after --script)
  --eval <js>          evaluate an expression in the page and print the result (repeatable)
  --script <file.mjs>  run interactions/assertions: export default async ({ page, expect, mode, url, log }) => {}
  --compare-http       also load the same page from a local http server and show what differs
  --root <dir>         http server root for --compare-http (default: the page's folder)
  --ignore <regex>     drop findings whose text matches (repeatable)
  --timeout <ms>       timeout for navigation and the whole --script, default 30000
                       (each click/fill/wait inside the script times out after 5000)
  --headed             show the browser window
  --browser-arg <arg>  extra browser command-line flag (repeatable)
  --json               print the full report as JSON
  -h, --help           show this help`;

// ---------- args ----------
let args;
try {
  args = parseArgs({
    allowPositionals: true,
    options: {
      browser: { type: 'string', default: 'chrome' },
      viewport: { type: 'string', default: '1280x800' },
      wait: { type: 'string', default: '500' },
      screenshot: { type: 'string' },
      eval: { type: 'string', multiple: true, default: [] },
      script: { type: 'string' },
      'compare-http': { type: 'boolean', default: false },
      root: { type: 'string' },
      ignore: { type: 'string', multiple: true, default: [] },
      timeout: { type: 'string', default: '30000' },
      headed: { type: 'boolean', default: false },
      'browser-arg': { type: 'string', multiple: true, default: [] },
      json: { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });
} catch (e) {
  fail(e.message + '\n\n' + USAGE);
}
const opt = args.values;
if (opt.help) { console.log(USAGE); process.exit(0); }
if (args.positionals.length !== 1) fail('Expected exactly one HTML file.\n\n' + USAGE);

const target = args.positionals[0];
const pagePath = path.resolve(target.startsWith('file:') ? fileURLToPath(target) : target);
if (!existsSync(pagePath) || !statSync(pagePath).isFile()) fail(`File not found: ${pagePath}`);
const fileUrl = pathToFileURL(pagePath).href;
const [vw, vh] = opt.viewport.split('x').map(Number);
if (!vw || !vh) fail(`Bad --viewport "${opt.viewport}", expected WxH like 390x844`);
const waitMs = Number(opt.wait);
const timeout = Number(opt.timeout);
const ignore = opt.ignore.map((r) => new RegExp(r, 'i'));
const serverRoot = path.resolve(opt.root ?? path.dirname(pagePath));
if (opt['compare-http'] && !pagePath.startsWith(serverRoot + path.sep)) fail(`--root ${serverRoot} does not contain ${pagePath}`);

let userScript;
if (opt.script) {
  const sp = path.resolve(opt.script);
  if (!existsSync(sp)) fail(`Script not found: ${sp}`);
  userScript = (await import(pathToFileURL(sp).href)).default;
  if (typeof userScript !== 'function') fail(`${sp} must "export default async ({ page, expect }) => {}"`);
}

// Use browsers downloaded into this repo (npm run install-browsers) when present.
if (!process.env.PLAYWRIGHT_BROWSERS_PATH && existsSync(path.join(ROOT, '.browsers'))) {
  process.env.PLAYWRIGHT_BROWSERS_PATH = path.join(ROOT, '.browsers');
}
let pw, expect;
try {
  pw = await import('playwright');
  ({ expect } = await import('@playwright/test'));
} catch {
  fail(`Dependencies are not installed. Run once:\n  npm install --prefix "${ROOT}"`);
}

// ---------- browser ----------
const engines = { chrome: 'chromium', chromium: 'chromium', firefox: 'firefox', webkit: 'webkit' };
const engineName = engines[opt.browser];
if (!engineName) fail(`Unknown --browser "${opt.browser}"`);
const RISKY_FLAGS = ['--allow-file-access-from-files', '--disable-web-security', '--allow-file-access', '--disable-site-isolation-trials'];

let browser;
try {
  browser = await pw[engineName].launch({
    headless: !opt.headed,
    args: opt['browser-arg'],
    ...(opt.browser === 'chrome' ? { channel: 'chrome' } : {}),
    // Playwright's Firefox turns this off by default, letting local files read
    // each other. Real Firefox keeps it on.
    ...(engineName === 'firefox' ? { firefoxUserPrefs: { 'security.fileuri.strict_origin_policy': true } } : {}),
  });
} catch (e) {
  const first = String(e.message).split('\n').slice(0, 3).join('\n');
  fail(`Could not launch ${opt.browser}: ${first}\n` +
    (opt.browser === 'chrome' ? 'Is Google Chrome installed?' : `Run: npm --prefix "${ROOT}" run install-browsers`));
}

const browserInfo = { name: opt.browser, version: browser.version(), headless: !opt.headed, fileIsolation: null, riskyFlags: [] };

// Canary: a real browser must block a file:// page from fetching its sibling.
// If this fetch succeeds, results would look healthier than real life.
{
  const dir = mkdtempSync(path.join(tmpdir(), 'filetest-canary-'));
  writeFileSync(path.join(dir, 'canary.txt'), 'x');
  writeFileSync(path.join(dir, 'canary.html'), '<!doctype html><title>canary</title>');
  const ctx = await browser.newContext();
  try {
    const page = await ctx.newPage();
    await page.goto(pathToFileURL(path.join(dir, 'canary.html')).href);
    const readable = await page.evaluate(() => fetch('canary.txt').then((r) => r.text()).then(() => true, () => false));
    browserInfo.fileIsolation = !readable;
  } catch { /* unknown */ } finally {
    await ctx.close();
    rmSync(dir, { recursive: true, force: true });
  }
}
if (engineName === 'chromium') {
  // Prove the browser enforces normal file:// security: read its real command line.
  try {
    const page = await browser.newPage();
    await page.goto('chrome://version');
    const argv = (await page.textContent('#command_line')).split(/\s+(?=--)/);
    await page.close();
    browserInfo.args = argv.slice(1);
    browserInfo.riskyFlags = browserInfo.args.filter((a) => RISKY_FLAGS.some((f) => a.startsWith(f)));
  } catch { browserInfo.riskyFlags = null; }
}

// ---------- run one load ----------
// Firefox reports blocked/missing local loads only as console warnings
// (Playwright does not surface file:// requests there), so treat them as errors.
const LOAD_FAILURE_WARNINGS = /Loading failed for the <script>|Module source URI is not allowed|Loading module from .* was blocked/i;
const isNoise = (url) => /\/favicon\.ico$/.test(url);

async function run(mode, url) {
  const r = {
    mode, url, title: null, loaded: false, navigationError: null,
    hazards: [], pageErrors: [], consoleErrors: [], consoleWarnings: [], consoleLogs: [],
    failedRequests: [], evals: [], script: null, screenshot: null, bodyText: null,
  };
  const context = await browser.newContext({ viewport: { width: vw, height: vh } });
  await context.addInitScript(HAZARD_SCRIPT);
  const page = await context.newPage();
  page.setDefaultTimeout(Math.min(timeout, 5000)); // per action; fail fast on a wrong selector
  page.setDefaultNavigationTimeout(timeout);

  page.on('console', (m) => {
    const text = m.text();
    if (text.startsWith(HAZARD_MARK)) {
      try { r.hazards.push(JSON.parse(text.slice(HAZARD_MARK.length))); } catch {}
      return;
    }
    // Chrome's generic "Failed to load resource" lines carry no URL; failedRequests has them.
    if (/^Failed to load resource/.test(text)) return;
    const t = m.type();
    if (t === 'error' || (t === 'warning' && LOAD_FAILURE_WARNINGS.test(text))) r.consoleErrors.push(text);
    else if (t === 'warning') r.consoleWarnings.push(text);
    else r.consoleLogs.push(`${t}: ${text}`);
  });
  page.on('pageerror', (e) => r.pageErrors.push(e.stack ? firstLines(e.stack, 4) : String(e.message)));
  page.on('requestfailed', (req) => {
    if (!isNoise(req.url())) r.failedRequests.push(`${req.url()}  (${req.failure()?.errorText ?? 'failed'})`);
  });
  page.on('response', (res) => {
    if (res.status() >= 400 && !isNoise(res.url())) r.failedRequests.push(`${res.url()}  (HTTP ${res.status()})`);
  });

  try {
    await page.goto(url, { waitUntil: 'load', timeout });
    r.loaded = true;
  } catch (e) {
    r.navigationError = firstLines(e.message, 2);
  }
  if (waitMs > 0) await page.waitForTimeout(waitMs);

  if (r.loaded) {
    r.title = await page.title().catch(() => null);
    for (const expr of opt.eval) {
      try {
        const value = await page.evaluate((src) => (0, eval)(src), expr); // promises are awaited
        r.evals.push({ expr, value });
      } catch (e) {
        r.evals.push({ expr, error: firstLines(e.message, 2) });
      }
    }
    if (userScript) {
      const logs = [];
      const started = Date.now();
      try {
        await withTimeout(userScript({ page, expect, mode, url, log: (...a) => logs.push(a.map(String).join(' ')) }), timeout);
        r.script = { passed: true, ms: Date.now() - started, logs };
      } catch (e) {
        r.script = { passed: false, ms: Date.now() - started, logs, error: firstLines(stripAnsi(e.message ?? String(e)), 12) };
      }
      await page.waitForTimeout(100); // let late console/errors from the script land
    }
    r.bodyText = await page.evaluate(() => document.body?.innerText ?? '').catch(() => null);
    if (opt.screenshot && mode === 'file') {
      r.screenshot = path.resolve(opt.screenshot);
      await page.screenshot({ path: r.screenshot, fullPage: true }).catch((e) => { r.screenshot = `failed: ${e.message}`; });
    }
  }
  await context.close();

  // Apply --ignore and de-dupe.
  const keep = (s) => !ignore.some((re) => re.test(s));
  for (const k of ['pageErrors', 'consoleErrors', 'consoleWarnings', 'consoleLogs', 'failedRequests']) r[k] = [...new Set(r[k])].filter(keep);
  r.hazards = r.hazards.filter((h) => keep(`${h.api}: ${h.detail}`));
  return r;
}

// ---------- static server for --compare-http ----------
const MIME = {
  '.html': 'text/html', '.htm': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.gif': 'image/gif', '.webp': 'image/webp', '.ico': 'image/x-icon', '.wasm': 'application/wasm', '.txt': 'text/plain',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.mp3': 'audio/mpeg', '.mp4': 'video/mp4', '.webm': 'video/webm',
};
function startServer(root) {
  const server = createServer(async (req, res) => {
    const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const p = path.join(root, rel);
    if (!p.startsWith(root)) { res.writeHead(403); return res.end(); }
    try {
      const target = statSync(p).isDirectory() ? path.join(p, 'index.html') : p;
      const body = await readFile(target);
      res.writeHead(200, { 'content-type': MIME[path.extname(target).toLowerCase()] ?? 'application/octet-stream' });
      res.end(body);
    } catch { res.writeHead(404); res.end(); }
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

// ---------- hints ----------
const HINTS = [
  [/Access to script at|Failed to load module script|module script|Module source URI is not allowed|\.m?js\s+\(Origin null is not allowed/i, 'module',
    'ES module scripts (type="module" src, import maps, import()) cannot load other files over file://. Inline the module code in the HTML or bundle to one classic <script>.'],
  [/^fetch|XMLHttpRequest|Access to (fetch|XMLHttpRequest)|Cross-Origin Request Blocked/i, 'fetch',
    'fetch()/XHR of local files is blocked on file://. Inline the data (e.g. <script type="application/json" id="data">) or let the user pick the file with <input type="file">.'],
  [/^(Shared)?Worker/i, 'worker',
    'Workers cannot load script files on file://. Build the worker from a Blob: new Worker(URL.createObjectURL(new Blob([code], {type: "text/javascript"}))).'],
  [/^history\.(push|replace)State/i, 'history',
    'pushState/replaceState to another path is blocked on file://. Use hash routing (location.hash / #/route).'],
  [/^(canvas|webgl)/i, 'canvas',
    'Images loaded from file:// taint the canvas, so reading pixels throws. Embed the image as a data: URL.'],
  [/^document\.cookie/i, 'cookie',
    'Cookies are not stored on file://. Use localStorage for local persistence.'],
  [/^iframe\.contentDocument/i, 'iframe',
    'Every file:// page is its own origin, so a parent cannot read a same-folder iframe. Use postMessage or srcdoc.'],
  [/^serviceWorker/i, 'sw',
    'Service workers are unavailable on file://. Guard registration with if (location.protocol !== "file:").'],
  [/ERR_FILE_NOT_FOUND|Loading failed for the <script>|Not allowed to load local resource/i, 'missing',
    'A referenced local file failed to load. Check it exists; root-relative URLs like "/app.js" resolve to file:///app.js (the disk root) under file://, so use "./app.js".'],
];
function hintsFor(r) {
  const lines = [
    ...r.hazards.map((h) => `${h.api}: ${h.detail}`),
    ...r.consoleErrors, ...r.failedRequests, ...r.pageErrors,
  ];
  const out = new Map();
  for (const line of lines) for (const [re, key, text] of HINTS) if (re.test(line)) out.set(key, text);
  return [...out.values()];
}

// ---------- compare ----------
function normalizer(httpBase) {
  const fileBase = pathToFileURL(serverRoot).href + '/';
  return (s) => String(s).split(fileBase).join('./').split(httpBase).join('./')
    .replace(/origin 'null'/g, "origin '<page>'").replace(/:\d+:\d+\)?/g, '');
}
function findingsOf(r, norm) {
  return [
    ...r.hazards.filter((h) => h.severity !== 'info').map((h) => `hazard ${h.api}: ${h.detail}`),
    ...r.pageErrors.map((s) => 'page error: ' + s.split('\n')[0]),
    ...r.consoleErrors.map((s) => 'console error: ' + s),
    ...r.failedRequests.map((s) => 'failed request: ' + s),
    ...(r.script && !r.script.passed ? ['script failed: ' + r.script.error.split('\n')[0]] : []),
  ].map(norm);
}
function compare(fileRun, httpRun, httpBase) {
  const norm = normalizer(httpBase);
  const a = findingsOf(fileRun, norm), b = findingsOf(httpRun, norm);
  const evalDiffs = fileRun.evals.map((e, i) => {
    const h = httpRun.evals[i];
    const fv = JSON.stringify(e.error ?? e.value), hv = JSON.stringify(h?.error ?? h?.value);
    return fv === hv ? null : { expr: e.expr, file: fv, http: hv };
  }).filter(Boolean);
  let textDiff = null;
  const ft = norm(fileRun.bodyText ?? ''), ht = norm(httpRun.bodyText ?? '');
  if (ft !== ht) {
    const fl = ft.split('\n'), hl = ht.split('\n');
    const i = fl.findIndex((l, k) => l !== hl[k]);
    const at = i === -1 ? fl.length : i;
    textDiff = { line: at + 1, file: fl[at] ?? '<end>', http: hl[at] ?? '<end>' };
  }
  return {
    httpUrl: httpRun.url,
    onlyFile: a.filter((x) => !b.includes(x)),
    onlyHttp: b.filter((x) => !a.includes(x)),
    evalDiffs, textDiff,
    httpScript: httpRun.script ? (httpRun.script.passed ? 'passed' : 'failed') : null,
  };
}

// ---------- main ----------
let report;
try {
  const fileRun = await run('file', fileUrl);
  let comparison = null;
  if (opt['compare-http']) {
    const server = await startServer(serverRoot);
    const base = `http://127.0.0.1:${server.address().port}/`;
    const rel = path.relative(serverRoot, pagePath).split(path.sep).map(encodeURIComponent).join('/');
    const httpRun = await run('http', base + rel);
    server.close();
    comparison = compare(fileRun, httpRun, base);
  }
  const issues = fileRun.hazards.filter((h) => h.severity === 'error').length + fileRun.pageErrors.length +
    fileRun.consoleErrors.length + fileRun.failedRequests.length +
    (fileRun.navigationError ? 1 : 0) + (fileRun.script && !fileRun.script.passed ? 1 : 0) +
    fileRun.evals.filter((e) => e.error).length;
  // A browser that lets local files read each other would hide file:// bugs.
  const reliable = browserInfo.fileIsolation === true;
  report = { ok: issues === 0 && reliable, reliable, issues, browser: browserInfo, file: fileRun, compare: comparison, hints: hintsFor(fileRun) };
} finally {
  await browser.close();
}

if (opt.json) console.log(JSON.stringify(report, null, 2));
else console.log(formatText(report));
process.exit(report.ok ? 0 : 1);

// ---------- text output ----------
function formatText(rep) {
  const r = rep.file;
  const out = [];
  const iso = rep.browser.fileIsolation;
  const flags = [
    iso === true ? 'file:// isolation enforced' : iso === false ? 'WARNING: file:// isolation NOT enforced, results are optimistic' : 'file:// isolation not checked',
    ...(rep.browser.riskyFlags?.length ? [`WARNING: launched with ${rep.browser.riskyFlags.join(' ')}`] : []),
    ...(rep.browser.name === 'firefox' ? ["Playwright's patched Firefox, close to but not identical to release Firefox"] : []),
    ...(rep.browser.name === 'webkit' ? ['Playwright WebKit, approximates Safari'] : []),
  ].join(' · ');
  out.push(`page     ${r.url}`);
  out.push(`browser  ${rep.browser.name} ${rep.browser.version}${rep.browser.headless ? ' (headless)' : ''} · ${flags}`);
  const counted = `${rep.issues} issue${rep.issues === 1 ? '' : 's'} under file://`;
  out.push(`result   ${!rep.reliable ? `UNRELIABLE, this browser does not enforce file:// isolation (${counted})`
    : rep.ok ? 'PASS, no issues under file://' : `FAIL, ${counted}`}`);
  if (r.title) out.push(`title    ${r.title}`);
  if (r.navigationError) out.push('', `✗ Navigation failed: ${r.navigationError}`);

  const section = (mark, name, items, fmt = (x) => x) => {
    if (!items.length) return;
    out.push('', `${mark} ${name} (${items.length})`);
    for (const it of items.slice(0, 30)) out.push(indent(fmt(it), '  - ', '    '));
    if (items.length > 30) out.push(`  … ${items.length - 30} more (use --json)`);
  };
  const errHaz = r.hazards.filter((h) => h.severity !== 'info');
  const infoHaz = r.hazards.filter((h) => h.severity === 'info');
  section('✗', 'file:// hazards', errHaz, (h) => `${h.api}: ${h.detail}${h.frame !== r.url ? `  [frame ${h.frame}]` : ''}`);
  section('✗', 'Page errors (uncaught)', r.pageErrors);
  section('✗', 'Console errors', r.consoleErrors);
  section('✗', 'Failed requests', r.failedRequests);
  section('!', 'Console warnings', r.consoleWarnings);
  section('i', 'Notes', infoHaz, (h) => `${h.api}: ${h.detail}`);
  section('·', 'Console output', r.consoleLogs);

  if (r.evals.length) {
    out.push('', 'Eval');
    for (const e of r.evals) out.push(`  ${e.expr}  =>  ${e.error ? 'ERROR ' + e.error : JSON.stringify(e.value)}`);
  }
  if (r.script) {
    out.push('', r.script.passed ? `✓ Script passed (${r.script.ms} ms)` : `✗ Script failed (${r.script.ms} ms)`);
    for (const l of r.script.logs) out.push(`  log: ${l}`);
    if (!r.script.passed) out.push(indent(r.script.error, '  ', '  '));
  }
  if (r.screenshot) out.push('', `screenshot  ${r.screenshot}`);

  const c = rep.compare;
  if (c) {
    out.push('', `── file:// vs ${c.httpUrl}`);
    const none = !c.onlyFile.length && !c.onlyHttp.length && !c.evalDiffs.length && !c.textDiff && !(r.script && c.httpScript && (r.script.passed ? 'passed' : 'failed') !== c.httpScript);
    if (none) out.push('  No differences: findings, eval results and page text match.');
    if (c.onlyFile.length) { out.push('  Only under file://:'); for (const x of c.onlyFile) out.push('    - ' + x); }
    if (c.onlyHttp.length) { out.push('  Only under http://:'); for (const x of c.onlyHttp) out.push('    - ' + x); }
    for (const d of c.evalDiffs) out.push(`  Eval differs: ${d.expr}\n    file: ${d.file}\n    http: ${d.http}`);
    if (c.textDiff) out.push(`  Page text differs at line ${c.textDiff.line}:\n    file: ${JSON.stringify(c.textDiff.file)}\n    http: ${JSON.stringify(c.textDiff.http)}`);
    if (r.script && c.httpScript && (r.script.passed ? 'passed' : 'failed') !== c.httpScript) {
      out.push(`  Script ${r.script.passed ? 'passed' : 'failed'} under file:// but ${c.httpScript} under http://`);
    }
  }
  if (rep.hints.length) {
    out.push('', 'How to fix');
    for (const h of rep.hints) out.push(indent(h, '  - ', '    '));
  }
  return out.join('\n');
}

// ---------- utils ----------
function fail(msg) { console.error(`filetest: ${msg}`); process.exit(2); }
function firstLines(s, n) { return String(s).split('\n').slice(0, n).join('\n'); }
function stripAnsi(s) { return String(s).replace(/\x1b\[[0-9;]*m/g, ''); }
function indent(s, first, rest) { return String(s).split('\n').map((l, i) => (i ? rest : first) + l).join('\n'); }
function withTimeout(p, ms) {
  let t;
  return Promise.race([p, new Promise((_, rej) => { t = setTimeout(() => rej(new Error(`--script timed out after ${ms} ms`)), ms); })])
    .finally(() => clearTimeout(t));
}
