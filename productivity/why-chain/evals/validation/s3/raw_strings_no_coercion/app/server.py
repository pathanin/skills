import json
import logging
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.settings import Settings, load_settings

log = logging.getLogger("inventory")


def make_handler(settings: Settings):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in settings.allowed_hosts:
                return self._send(400, {"error": "bad host"})
            if self.path == "/health":
                return self._send(200, {"ok": True})
            if self.path.startswith("/stock/"):
                sku = self.path.removeprefix("/stock/")
                with sqlite3.connect(settings.db_path) as conn:
                    row = conn.execute("SELECT qty FROM stock WHERE sku = ?", (sku,)).fetchone()
                if row is None:
                    return self._send(404, {"error": "unknown sku"})
                return self._send(200, {"sku": sku, "qty": row[0]})
            return self._send(404, {"error": "not found"})

        def log_message(self, fmt, *args):
            if settings.debug:
                log.debug(fmt, *args)

    return Handler


def main() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)
    log.info("listening on :%s (db=%s)", settings.port, settings.db_path)
    ThreadingHTTPServer(("0.0.0.0", settings.port), make_handler(settings)).serve_forever()
