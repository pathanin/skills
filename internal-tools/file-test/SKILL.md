---
name: file-test
description: Test a local single-file HTML page the way users actually open it, over file:// (double-click), in a real browser. Use whenever you build, change or verify a standalone .html file, or the user says a page "works on the server but not when opened directly". Reports blocked module scripts, fetch/XHR, workers, tainted canvas, dropped cookies, pushState and root-relative paths, including failures the page catches silently. Do not substitute python -m http.server; serving over http hides exactly these bugs.
---

# file-test

`filetest` loads an HTML file over **file://** in your installed Google Chrome (or
Playwright's Firefox/WebKit) and prints what broke. Serving the page over http
hides a whole class of bugs that only appear when someone double-clicks the file,
so test the file directly.

```bash
node "${CLAUDE_SKILL_DIR}/scripts/filetest.mjs" page.html [options]
```

If `${CLAUDE_SKILL_DIR}` is not an absolute path, use the "Base directory for this
skill" path shown when the skill loads.

Exit code: `0` clean, `1` issues found, `2` tool error (bad path, browser missing,
dependencies not installed).

**First run:** if it exits 2 with "Dependencies are not installed", run
`npm install --prefix "${CLAUDE_SKILL_DIR}"` once. `--browser firefox|webkit` also
needs `npm --prefix "${CLAUDE_SKILL_DIR}" run install-browsers` (downloads into the
skill folder). The default, `chrome`, uses the installed Google Chrome.

## Workflow

1. After writing or changing an HTML file, run `filetest page.html`.
2. Read the report and fix every `✗` item. "How to fix" gives the file://-safe
   pattern for each problem found; those patterns are verified to work on file://.
3. Test behavior, not just loading. Write a small `--script` that clicks through
   the main feature and asserts the result with `expect`.
4. Re-run until `result PASS`. Add `--screenshot` when layout matters, then Read
   the PNG to look at it.
5. If the page will be opened in Safari or Firefox, re-run with `--browser webkit`
   and `--browser firefox`. The engines differ on file://.

## Options

| Option | Use |
|---|---|
| `--eval "<js>"` | Print an expression's value, e.g. `--eval "document.querySelector('#total').textContent"`. Repeatable. Promises are awaited. |
| `--script t.mjs` | Run interactions and assertions (see below). |
| `--screenshot out.png` | Full-page PNG, taken after load and after `--script` if one is given. |
| `--viewport 390x844` | Mobile size. The default is 1280x800. |
| `--wait <ms>` | Settle time after load. The default is 500. Raise it for animations or timers. |
| `--compare-http` | Also load the page from a local http server and list what differs. Shows which problems are specific to file://. |
| `--root <dir>` | Server root for `--compare-http` if the page references `../` files. |
| `--browser chrome\|firefox\|webkit` | `chrome` (default) is real Chrome. `webkit` approximates Safari. |
| `--ignore <regex>` | Drop known, accepted findings. Repeatable. |
| `--json` | Machine-readable full report. |
| `--headed` | Show the window. Only when the user wants to watch. |

## --script

Write the script to the scratchpad, not the user's project, unless they want it kept.

```js
// t.mjs: page is a Playwright Page, expect is Playwright's auto-waiting expect.
export default async ({ page, expect, log, mode }) => {
  await page.fill('#name', 'Ada');
  await page.click('text=Save');
  await expect(page.locator('#status')).toHaveText('Saved');
  await page.reload();                                   // persistence check
  await expect(page.locator('#name')).toHaveValue('Ada');
  log('items:', await page.locator('li').count());       // shows up in the report
};
```

Do not `import` Playwright in the script; use the `page` and `expect` it receives.
`mode` is `'file'` or `'http'` (under `--compare-http` the script runs in both modes).

## Reading the report

- **file:// hazards**: an API failed because of file://, even if the page caught the
  error and carried on. These are the bugs a server-based test misses.
- **Page errors / Console errors / Failed requests**: what the browser reported.
- **Notes (i)**: not failures. For example, localStorage on file:// is shared by
  every local HTML file in Chrome, so prefix keys.
- **result UNRELIABLE** (exit 1): the browser lets local files read each other,
  so the run proves nothing. Do not pass extra `--browser-arg` flags that relax security.

Engine caveats: under `--browser firefox`, a missing stylesheet or image produces
no finding (only scripts are reported), so check missing assets with Chrome. Under
`--browser webkit`, a failure the page catches can still be listed as "Page errors
(uncaught)".

## What breaks on file:// (observed in Chrome 155)

Per-engine table, how the probes work and known limits: `references/file-behavior.md`.


- `<script type="module" src>`, import maps, and `import()` of local files.
  Inline modules with no imports work.
- `fetch`/XHR of local files. Inline the data in `<script type="application/json">`.
- `new Worker('w.js')`. Use a Blob URL worker.
- `history.pushState` to another path. Use `#hash` routes.
- Reading pixels from a canvas after drawing a local image. Use a data: URL image.
- Reading a same-folder iframe's document. Use `srcdoc` or `postMessage`.
- Cookies and service workers.
- `/abs/path.js` resolves to the disk root. Use `./path.js`.
