// Regression tests: each fixture's expected file:// outcome was first observed
// in real Chrome (see README "Verified behavior"), then pinned here.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const bin = path.join(here, '..', 'scripts', 'filetest.mjs');
const fx = (f) => path.join(here, 'fixtures', f);
const browser = process.env.FILETEST_BROWSER ?? 'chrome';
const engine = browser === 'chrome' ? 'chromium' : browser;
// Pick the observed value for the current engine ({ chromium, firefox, webkit, default }).
const per = (o) => (engine in o ? o[engine] : o.default);

function filetest(file, ...flags) {
  const p = spawnSync(process.execPath, [bin, file, '--json', '--browser', browser, ...flags], { encoding: 'utf8', timeout: 90_000 });
  if (p.status === 2 || !p.stdout) throw new Error(`filetest crashed (${p.status}): ${p.stderr}`);
  return { code: p.status, report: JSON.parse(p.stdout) };
}
const outText = '--eval=document.getElementById("out")?.textContent';
const hazardApis = (r) => r.file.hazards.filter((h) => h.severity !== 'info').map((h) => h.api);
const all = (r) => JSON.stringify(r.file);

test('clean page passes with exit 0 and captures console output', () => {
  const { code, report } = filetest(fx('ok.html'));
  assert.equal(code, 0);
  assert.equal(report.ok, true);
  assert.equal(report.file.title, 'OK page');
  assert.deepEqual(report.file.consoleLogs, ['log: ready']);
});

test('browser launch has no file-access override flags', () => {
  const { report } = filetest(fx('ok.html'));
  if (browser === 'chrome' || browser === 'chromium') assert.deepEqual(report.browser.riskyFlags, []);
});

const blocked = [
  ['module.html', /mod\.js/, 'module'],
  ['importmap.html', /mod\.js/, 'module'],
  ['fetch.html', /fetch/, 'fetch'],
  ['xhr.html', /XMLHttpRequest/, 'fetch'],
];
for (const [file, pattern, hint] of blocked) {
  test(`${file}: blocked load is reported and the page breaks`, () => {
    const { code, report } = filetest(fx(file), outText);
    assert.equal(code, 1);
    assert.match(all(report), pattern);
    assert.notEqual(report.file.evals[0].value, '42');
    assert.ok(report.hints.some((h) => h.toLowerCase().includes(hint)), `expected a ${hint} hint, got ${report.hints}`);
  });
}

test('fetch failure is caught by the page but still reported', () => {
  const { code, report } = filetest(fx('fetch-caught.html'), outText);
  assert.equal(code, 1);
  // Playwright's WebKit surfaces the blocked fetch as a page error even when caught.
  if (engine !== 'webkit') assert.equal(report.file.pageErrors.length, 0, 'page swallowed the error');
  assert.ok(hazardApis(report).includes('fetch'));
  assert.equal(report.file.evals[0].value, 'fallback');
});

// Chromium throws from new Worker(); Firefox/WebKit fire an error event instead.
// Firefox/WebKit keep cookies on file://, Chromium drops them.
const silent = [
  ['worker.html', 'Worker', per({ chromium: 'throw:SecurityError', default: 'worker error' })],
  ['pushstate.html', 'history.pushState', 'blocked:SecurityError'],
  ['canvas.html', 'canvas.getImageData', 'tainted:SecurityError'],
  ['iframe.html', 'iframe.contentDocument', 'blocked:TypeError'],
  ['storage.html', 'document.cookie', null, engine === 'chromium'],
  ['sw.html', 'serviceWorker.register', null],
];
for (const [file, api, out, applies = true] of silent) {
  test(`${file}: silently-caught ${api} failure is reported as a hazard`, { skip: !applies && `${engine} allows this on file://` }, () => {
    const { code, report } = filetest(fx(file), outText);
    assert.equal(code, 1);
    assert.ok(hazardApis(report).includes(api), `hazards: ${hazardApis(report)}`);
    if (out) assert.equal(report.file.evals[0].value, out);
  });
}

test('uncaught exception is a page error', () => {
  const { code, report } = filetest(fx('throws.html'));
  assert.equal(code, 1);
  assert.match(report.file.pageErrors[0], /undefinedFn/);
});

test('root-relative paths resolve to the disk root and get the right hint', () => {
  const { code, report } = filetest(fx('rootpath.html'));
  assert.equal(code, 1);
  assert.match(all(report), /file:\/\/\/app\.js/); // engines report it as a failed request or console error
  assert.ok(report.hints.some((h) => /root-relative/i.test(h)));
});

test('the fixes the hints recommend actually work on file://', () => {
  const { code, report } = filetest(fx('fixed-patterns.html'), '--wait=800');
  assert.equal(code, 0, all(report));
  const text = report.file.bodyText;
  for (const s of ['blob worker 42', 'inline json 42', 'inline module ok', 'hash #/settings', 'data url canvas readable', 'srcdoc inline child']) {
    assert.ok(text.includes(s), `missing "${s}" in ${JSON.stringify(text)}`);
  }
});

test('localStorage use is a note, not a failure', () => {
  const { code, report } = filetest(path.join(here, 'counter.html'), '--script', path.join(here, 'scripts', 'counter.mjs'));
  assert.equal(code, 0);
  assert.ok(report.file.hazards.some((h) => h.api === 'localStorage' && h.severity === 'info'));
  assert.equal(report.hints.length, 0);
});

test('--script passes, with logs and expect()', () => {
  const { code, report } = filetest(path.join(here, 'counter.html'), '--script', path.join(here, 'scripts', 'counter.mjs'));
  assert.equal(code, 0);
  assert.equal(report.file.script.passed, true);
  assert.deepEqual(report.file.script.logs, ['count after two clicks: 2']);
});

test('--script failure fails the run with the assertion message', () => {
  const { code, report } = filetest(path.join(here, 'counter.html'), '--script', path.join(here, 'scripts', 'failing.mjs'));
  assert.equal(code, 1);
  assert.equal(report.file.script.passed, false);
  assert.match(report.file.script.error, /Expected: "99"/);
});

test('--compare-http shows what only breaks under file://', () => {
  const { report } = filetest(fx('fetch-caught.html'), outText, '--compare-http');
  const c = report.compare;
  assert.ok(c.onlyFile.some((x) => x.includes('fetch')));
  assert.deepEqual(c.onlyHttp, []);
  assert.deepEqual(c.evalDiffs[0], { expr: outText.slice(7), file: '"fallback"', http: '"42"' });
  assert.equal(c.textDiff.file, 'fallback');
});

test('--compare-http reports no differences for a portable page', () => {
  const { report } = filetest(fx('fixed-patterns.html'), '--compare-http', '--wait=800');
  assert.deepEqual([report.compare.onlyFile, report.compare.onlyHttp, report.compare.textDiff], [[], [], null]);
});

test('--screenshot writes a PNG', async () => {
  const { mkdtempSync, readFileSync } = await import('node:fs');
  const { tmpdir } = await import('node:os');
  const out = path.join(mkdtempSync(path.join(tmpdir(), 'filetest-')), 'shot.png');
  filetest(fx('ok.html'), '--screenshot', out);
  assert.equal(readFileSync(out).subarray(1, 4).toString(), 'PNG');
});

test('missing file is a tool error (exit 2)', () => {
  const p = spawnSync(process.execPath, [bin, fx('nope.html')], { encoding: 'utf8' });
  assert.equal(p.status, 2);
  assert.match(p.stderr, /File not found/);
});

test('canary: file:// isolation is enforced by default', () => {
  const { report } = filetest(fx('ok.html'));
  assert.equal(report.browser.fileIsolation, true);
});

test('canary: a browser that lets local files read each other is flagged', { skip: !browser.startsWith('chrom') }, () => {
  const p = spawnSync(process.execPath, [bin, fx('ok.html'), '--browser', browser, '--browser-arg=--allow-file-access-from-files'], { encoding: 'utf8', timeout: 90_000 });
  assert.match(p.stdout, /WARNING: file:\/\/ isolation NOT enforced/);
  assert.match(p.stdout, /WARNING: launched with --allow-file-access-from-files/);
  assert.match(p.stdout, /result   UNRELIABLE/);
  assert.equal(p.status, 1, 'an unreliable run must not exit 0');
});

test('--script with a wrong selector fails fast and names the locator', () => {
  const started = Date.now();
  const { code, report } = filetest(fx('ok.html'), '--script', path.join(here, 'scripts', 'counter.mjs'));
  assert.equal(code, 1);
  assert.match(report.file.script.error, /#inc/);
  assert.ok(Date.now() - started < 15_000, 'should not wait for the 30s default');
});

test('an uncaught fetch rejection stays a page error (probes do not swallow it)', () => {
  const { code, report } = filetest(fx('fetch-bare.html'));
  assert.equal(code, 1);
  assert.ok(report.file.pageErrors.some((e) => /fetch|load/i.test(e)), JSON.stringify(report.file.pageErrors));
  assert.ok(hazardApis(report).includes('fetch'));
});

test('page unhandledrejection listeners still fire', () => {
  const { report } = filetest(fx('fetch-bare.html'), '--eval=window.__unhandled');
  assert.equal(report.file.evals[0].value, true);
});
