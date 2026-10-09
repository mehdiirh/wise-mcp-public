"""Versioned, timestamp-bound proof of origin for the Wise backend."""

import hashlib
import hmac
import json
import time

import httpx


def signature_payload(
    method: str, target: str, content_type: str, timestamp: str, body: bytes, authorization: str
) -> bytes:
    # Match backend/core/mcp_signing.py; changes require a new protocol version.
    return json.dumps(
        [
            "wise-mcp-v1",
            method.upper(),
            target,
            content_type.lower(),
            timestamp,
            hashlib.sha256(body).hexdigest(),
            hashlib.sha256(authorization.encode("utf-8")).hexdigest(),
        ],
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


class MCPRequestSigner(httpx.Auth):
    requires_request_body = True

    def __init__(self, secret: str):
        self._key = bytes.fromhex(secret)

    def auth_flow(self, request: httpx.Request):
        timestamp = str(int(time.time()))
        payload = signature_payload(
            request.method,
            request.url.raw_path.decode("ascii"),
            request.headers.get("content-type", ""),
            timestamp,
            request.content,
            request.headers.get("authorization", ""),
        )
        request.headers["X-Wise-MCP-Timestamp"] = timestamp
        request.headers["X-Wise-MCP-Signature"] = (
            "v1=" + hmac.new(self._key, payload, hashlib.sha256).hexdigest()
        )
        yield request
