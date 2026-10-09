"""Local UI preview with synthetic data only: uv run python scripts/preview_ui.py."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (Path(__file__).with_name("preview.html")).read_text()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            content = PREVIEW.encode()
        elif self.path == "/results.html":
            content = (ROOT / "ui/results.html").read_bytes()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    print("Synthetic UI preview: http://127.0.0.1:8765", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
