# file:// behavior and how filetest works

## Verified behavior

Observed with the fixtures in `test/fixtures/` (Playwright 1.64.0). ✗ = fails on
file://, ✓ = works.

| Feature | Chrome 155 | Firefox 157 (Playwright) | WebKit 27.2 (Playwright) |
|---|---|---|---|
| `<script type="module" src>`, import maps | ✗ | ✗ | ✗ |
| `fetch` / XHR of a sibling file | ✗ | ✗ | ✗ |
| `new Worker('w.js')` | ✗ (throws) | ✗ (error event) | ✗ (error event) |
| `history.pushState` to another path | ✗ | ✗ | ✗ |
| canvas `getImageData` after a local image | ✗ | ✗ | ✗ |
| read a same-folder iframe's document | ✗ | ✗ | ✗ |
| service worker register | ✗ | ✗ | ✗ |
| cookies | ✗ (dropped) | ✓ | ✓ |
| `src="/app.js"` (root-relative) | ✗ (disk root) | ✗ | ✗ |
| localStorage | ✓, shared by all file:// pages | ✓ | ✓ |
| Blob worker, inline JSON, `#hash` routes, data: URL images, inline modules | ✓ | ✓ | ✓ |

## How it works

- **Real browser, normal security.** `--browser chrome` (default) drives the
  installed Google Chrome. Firefox and WebKit are Playwright builds.
- **Isolation canary.** Every launch loads a temp page over file:// that tries to
  `fetch` a sibling file. If the fetch succeeds, the result is UNRELIABLE (exit 1).
  This guards against a launch flag or preference that relaxes file:// security.
  Playwright's Firefox ships with `security.fileuri.strict_origin_policy=false`;
  filetest turns it back on.
- **Hazard probes** (`scripts/hazards.js`) run before page scripts. They wrap the
  APIs that fail on file:// (Worker, fetch, XHR, pushState, canvas reads, cookies,
  iframe access, service workers) so a failure is reported even when the page
  catches it. Rejections are rethrown, so page behavior is unchanged.
- **`--compare-http`** loads the same page from a throwaway local server and diffs
  findings, `--eval` results and page text.

## Limits

- Playwright's Firefox and WebKit are patched builds, close to but not identical
  to release Firefox and Safari. Real Safari cannot be automated this way.
- **Firefox misses some failed loads.** Playwright's Firefox emits no request
  events for file://. A missing or blocked script still shows up as a console
  warning, but a missing stylesheet or image produces no finding. Use Chrome to
  check for missing assets.
- **WebKit can mislabel caught errors.** It reports some caught failures (such as
  a blocked `fetch` the page handles) under "Page errors (uncaught)".
- Hazard probes see only the APIs they wrap. Use `--compare-http` and a `--script`
  that asserts visible behavior to catch anything else.

## Tests

```bash
npm --prefix "${CLAUDE_SKILL_DIR}" test          # Chrome
npm --prefix "${CLAUDE_SKILL_DIR}" run test:all  # Chrome, Firefox, WebKit
```
