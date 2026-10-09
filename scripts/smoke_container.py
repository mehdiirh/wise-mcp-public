"""Exercise the built image over real HTTP, using a loopback fake Wise backend."""

import asyncio
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import httpx
from fastmcp import Client

seen = []


class Backend(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        fields = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        action = fields["method"][0]
        token = self.headers.get("Authorization")
        assert not self.headers.get("Cookie")
        assert not self.headers.get("X-User-ID")
        seen.append((action, token))
        valid = token in {"Bearer alice-smoke", "Bearer bob-smoke"}
        data = {"global_id": token, "is_active": True} if action == "get_me" else []
        body = json.dumps(
            {
                "data": data,
                "extra": None,
                "meta": {
                    "success": valid,
                    "status": 200 if valid else 400,
                    "code": None if valid else "AUTHORIZATION_FAILED",
                },
            }
        ).encode()
        self.send_response(200 if valid else 400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


async def check():
    async def user(token):
        async with Client("http://127.0.0.1:8000/wise-mcp", auth=token) as client:
            tools = await client.list_tools()
            assert len(tools) == 23
            assert all(tool.annotations.readOnlyHint for tool in tools)
            result = await client.call_tool("get_me", {})
            assert result.structured_content["data"]["global_id"] == f"Bearer {token}"
            resource = await client.read_resource("ui://wise-public/results.html")
            assert resource[0].mimeType == "text/html;profile=mcp-app"
            assert "ui/initialize" in resource[0].text

    await asyncio.gather(user("alice-smoke"), user("bob-smoke"))
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/wise-mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={
                "Authorization": "Bearer invalid-smoke",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert response.status_code == 401


if __name__ == "__main__":
    assert os.getuid() == 10001, "Smoke test must run with the image's non-root user"
    backend = ThreadingHTTPServer(("127.0.0.1", 9999), Backend)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    process = subprocess.Popen(
        ["python", "server.py"],
        env={**os.environ, "WISE_API_BASE_URL": "http://127.0.0.1:9999/api"},
    )
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                assert httpx.get("http://127.0.0.1:8000/healthz").json()["read_only"] is True
                break
            except httpx.ConnectError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)
        asyncio.run(check())
        print("PASS: non-root startup, health, 23 tools, isolated bearer tokens, UI, invalid auth")
    finally:
        process.terminate()
        process.wait(timeout=10)
        backend.shutdown()
