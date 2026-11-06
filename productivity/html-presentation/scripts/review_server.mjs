// Review server for an HTML deck: serves DECK/ on http://127.0.0.1:8765 and saves the
// reviewer's text edits and comments to DECK/review.json (read by Claude to apply them).
//   node review_server.mjs DECK [--open]       (review.cmd in the project runs this)
// Plain Node, no packages. Only listens on localhost. Ctrl+C to stop.
import { createServer } from "node:http";
import { readFileSync, writeFileSync, statSync, createReadStream, existsSync, renameSync } from "node:fs";
import { join, resolve, dirname, extname, sep } from "node:path";
import { spawn } from "node:child_process";

const deckArg = process.argv.slice(2).find((a) => !a.startsWith("--"));
if (!deckArg) { console.error("usage: node review_server.mjs DECK [--open]"); process.exit(2); }
const ROOT = resolve(deckArg);
const REVIEW = join(ROOT, "review.json");
const PORT = Number(process.env.PORT || 8765);
const TYPES = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
  ".svg": "image/svg+xml", ".mp4": "video/mp4", ".ttf": "font/ttf", ".woff2": "font/woff2" };
const EMPTY = { edits: {}, comments: [] };

function readReview() {
  try { return JSON.parse(readFileSync(REVIEW, "utf-8")); } catch { return EMPTY; }
}

createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  if (url.pathname === "/api/review") {
    if (req.method === "GET") {
      res.writeHead(200, { "content-type": TYPES[".json"], "cache-control": "no-store" });
      return res.end(JSON.stringify(readReview()));
    }
    if (req.method === "POST") {
      let body = "";
      req.on("data", (c) => { body += c; if (body.length > 5e6) req.destroy(); });
      req.on("end", () => {
        try {
          const data = JSON.parse(body);
          if (typeof data !== "object" || !data.edits || !Array.isArray(data.comments)) throw new Error("bad shape");
          writeFileSync(REVIEW + ".tmp", JSON.stringify(data, null, 2) + "\n", "utf-8");
          renameSync(REVIEW + ".tmp", REVIEW);            // never leave a half-written file
          res.writeHead(200, { "content-type": TYPES[".json"] }); res.end('{"ok":true}');
        } catch (e) { res.writeHead(400); res.end(String(e.message)); }
      });
      return;
    }
  }
  // static files under html/ (with Range support so clips can seek)
  let p = decodeURIComponent(url.pathname); if (p === "/") p = "/index.html";
  const file = resolve(join(ROOT, p));
  if (!file.startsWith(ROOT + sep) || !existsSync(file) || !statSync(file).isFile()) { res.writeHead(404); return res.end("not found"); }
  const size = statSync(file).size, type = TYPES[extname(file).toLowerCase()] || "application/octet-stream";
  const range = /bytes=(\d*)-(\d*)/.exec(req.headers.range || "");
  if (range) {
    const start = range[1] ? Number(range[1]) : size - Number(range[2]);
    const end = range[1] && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    res.writeHead(206, { "content-type": type, "content-range": `bytes ${start}-${end}/${size}`, "accept-ranges": "bytes", "content-length": end - start + 1 });
    return createReadStream(file, { start, end }).pipe(res);
  }
  res.writeHead(200, { "content-type": type, "content-length": size, "accept-ranges": "bytes", "cache-control": "no-cache" });
  createReadStream(file).pipe(res);
}).on("error", (e) => { console.error(e.code === "EADDRINUSE" ? `port ${PORT} is busy (another review window open?). Set PORT=8766 to use another.` : e.message); process.exit(1); })
  .listen(PORT, "127.0.0.1", () => {
  const u = `http://127.0.0.1:${PORT}/`;
  console.log(`Review mode: ${u}   (edits/comments -> ${REVIEW}; close this window to stop)`);
  if (process.argv.includes("--open")) spawn("cmd", ["/c", "start", "", u], { stdio: "ignore", detached: true }).unref();
});
