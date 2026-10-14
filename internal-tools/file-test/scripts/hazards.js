// Injected before any page script (Playwright addInitScript). Wraps browser APIs
// that behave differently under file:// so failures are reported even when the
// page catches them. Each finding is emitted as a console.debug message with a
// marker prefix; the runner pulls those out of the console stream.
(() => {
  if (window.__filetestHazardsInstalled) return;
  window.__filetestHazardsInstalled = true;

  const MARK = '[filetest-hazard]';
  const debug = console.debug.bind(console);
  const seen = new Set();
  const report = (api, severity, detail) => {
    const key = api + '|' + detail;
    if (seen.has(key)) return;
    seen.add(key);
    try { debug(MARK + JSON.stringify({ api, severity, detail, frame: location.href })); } catch {}
  };
  const describe = (e) => (e && (e.name ? e.name + ': ' + e.message : String(e))) || 'unknown error';

  // Wrap a method so a throw is reported (then rethrown unchanged).
  const wrapThrow = (proto, name, api) => {
    const orig = proto && proto[name];
    if (typeof orig !== 'function') return;
    proto[name] = function (...args) {
      try { return orig.apply(this, args); }
      catch (e) { report(api, 'error', describe(e)); throw e; }
    };
  };

  // Wrap a constructor so a throw is reported.
  const wrapCtor = (name) => {
    const Orig = window[name];
    if (typeof Orig !== 'function') return;
    const Wrapped = function (...args) {
      let w;
      try { w = new Orig(...args); }
      catch (e) { report(name, 'error', `new ${name}(${JSON.stringify(String(args[0]))}) threw ${describe(e)}`); throw e; }
      // Firefox and WebKit fail asynchronously instead of throwing. Blob/data
      // workers are skipped so a genuine script error is not misread as a block.
      const src = String(args[0]);
      if (!/^(blob|data):/.test(src)) {
        w.addEventListener('error', (ev) => {
          if (!ev.message) report(name, 'error', `new ${name}(${JSON.stringify(src)}) failed to load`);
        });
      }
      return w;
    };
    Wrapped.prototype = Orig.prototype;
    Object.setPrototypeOf(Wrapped, Orig);
    window[name] = Wrapped;
  };

  wrapCtor('Worker');
  wrapCtor('SharedWorker');

  wrapThrow(History.prototype, 'pushState', 'history.pushState');
  wrapThrow(History.prototype, 'replaceState', 'history.replaceState');

  if (window.CanvasRenderingContext2D) wrapThrow(CanvasRenderingContext2D.prototype, 'getImageData', 'canvas.getImageData');
  if (window.HTMLCanvasElement) {
    wrapThrow(HTMLCanvasElement.prototype, 'toDataURL', 'canvas.toDataURL');
    wrapThrow(HTMLCanvasElement.prototype, 'toBlob', 'canvas.toBlob');
  }
  if (window.WebGLRenderingContext) wrapThrow(WebGLRenderingContext.prototype, 'texImage2D', 'webgl.texImage2D');
  if (window.WebGL2RenderingContext) wrapThrow(WebGL2RenderingContext.prototype, 'texImage2D', 'webgl2.texImage2D');

  // fetch: rejected promises are reported even if the page catches them. The
  // page gets a rethrowing promise, so an uncaught rejection stays unhandled.
  const origFetch = window.fetch;
  if (typeof origFetch === 'function') {
    window.fetch = function (input, init) {
      const url = typeof input === 'string' ? input : (input && input.url) || String(input);
      return origFetch.call(this, input, init).catch((e) => {
        report('fetch', 'error', `fetch(${JSON.stringify(url)}) rejected: ${describe(e)}`);
        throw e;
      });
    };
  }

  // XMLHttpRequest: network-level error event (CORS block, missing file).
  if (window.XMLHttpRequest) {
    const origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
      this.addEventListener('error', () => report('XMLHttpRequest', 'error', `${method} ${JSON.stringify(String(url))} failed (error event)`));
      return origOpen.call(this, method, url, ...rest);
    };
  }

  // Service workers are unavailable on file:// (register rejects).
  if (navigator.serviceWorker && navigator.serviceWorker.register) {
    const container = navigator.serviceWorker;
    const origRegister = container.register.bind(container);
    container.register = function (url, opts) {
      return origRegister(url, opts).catch((e) => {
        report('serviceWorker.register', 'error', `register(${JSON.stringify(String(url))}) rejected: ${describe(e)}`);
        throw e;
      });
    };
  }

  // Cookies: writes are silently dropped on file://.
  const cookieDesc = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
  if (cookieDesc && cookieDesc.set && cookieDesc.get) {
    Object.defineProperty(Document.prototype, 'cookie', {
      configurable: true,
      enumerable: cookieDesc.enumerable,
      get() { return cookieDesc.get.call(this); },
      set(v) {
        cookieDesc.set.call(this, v);
        const pair = String(v).split(';')[0];
        const name = pair.split('=')[0].trim();
        const deleting = /expires=thu, 01 jan 1970|max-age=0/i.test(String(v));
        if (name && !deleting && !cookieDesc.get.call(this).split('; ').some((c) => c.split('=')[0] === name)) {
          report('document.cookie', 'error', `cookie "${name}" was not stored`);
        }
      },
    });
  }

  // Same-folder iframes are cross-origin on file:// so contentDocument is null.
  const docDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentDocument');
  if (docDesc && docDesc.get) {
    Object.defineProperty(HTMLIFrameElement.prototype, 'contentDocument', {
      configurable: true,
      enumerable: docDesc.enumerable,
      get() {
        const d = docDesc.get.call(this);
        if (d === null && this.getAttribute('src')) report('iframe.contentDocument', 'error', `contentDocument is null for iframe src=${JSON.stringify(this.getAttribute('src'))}`);
        return d;
      },
    });
  }

  // localStorage works, but in Chrome every file:// page shares one origin.
  try {
    const origSet = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) {
      if (location.protocol === 'file:' && this === window.localStorage) {
        report('localStorage', 'info', 'localStorage on file:// is shared by every local HTML file (origin "file://" in Chrome); keys can collide');
      }
      return origSet.call(this, k, v);
    };
  } catch {}

  // Errors the page swallows via window.onerror still surface as pageerror;
  // unhandled rejections too. Nothing extra needed here.
})();
