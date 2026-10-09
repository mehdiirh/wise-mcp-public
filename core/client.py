"""Fixed-origin, bounded requests. No cookies, redirects, retries, or shared credentials."""

import json
import re
from typing import Any

import httpx

from core.config import Settings
from core.policy import check_action

USER_AGENT = "wise-mcp-public/1.0.0"


class WiseAPIError(Exception):
    def __init__(self, code: str, message: str, *, status: int = 502):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"{code}: {message}")


def safe_text(value: Any, token: str, default: str) -> str:
    if not isinstance(value, str):
        return default
    value = value.replace(token, "[redacted]") if token else value
    value = re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", value)
    return value[:500]


class WiseClient:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def call(
        self, route: str, action: str, *, token: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        params = params or {}
        check_action(route, action, params)
        if not token or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in token):
            raise WiseAPIError("NOT_AUTHENTICATED", "A Wise bearer token is required", status=401)
        form = {
            k: str(v).lower() if isinstance(v, bool) else str(v)
            for k, v in params.items()
            if v is not None
        }
        form["method"] = action
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/csv",
            "User-Agent": USER_AGENT,
        }
        # A fresh client deliberately discards backend Set-Cookie headers per call.
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                async with client.stream(
                    "POST", self.settings.api_base_url + route, data=form, headers=headers
                ) as response:
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > self.settings.max_response_bytes:
                            raise WiseAPIError(
                                "RESPONSE_TOO_LARGE", "Narrow the query or request a smaller page"
                            )
                    status = response.status_code
                    content_type = response.headers.get("content-type", "").split(";")[0]
        except httpx.TimeoutException:
            raise WiseAPIError(
                "UPSTREAM_TIMEOUT", "Wise API did not respond in time", status=504
            ) from None
        except httpx.HTTPError:
            raise WiseAPIError("UPSTREAM_UNAVAILABLE", "Wise API could not be reached") from None

        if 300 <= status < 400:
            raise WiseAPIError("UPSTREAM_REDIRECT", "Wise API returned an unexpected redirect")
        if status == 429:
            raise WiseAPIError(
                "RATE_LIMITED", "Wise API rate limit reached; try again later", status=429
            )
        if status >= 500:
            raise WiseAPIError("UPSTREAM_UNAVAILABLE", "Wise API returned a server error")
        if content_type == "text/csv" and status == 200 and params.get("as_csv") is True:
            try:
                csv = chunks.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise WiseAPIError("INVALID_RESPONSE", "Wise returned invalid CSV") from None
            return {
                "data": csv,
                "extra": {"format": "csv", "ad_code": params.get("ad_code")},
                "meta": {"status": status, "success": True},
            }
        try:
            payload = json.loads(chunks)
        except (ValueError, UnicodeDecodeError):
            raise WiseAPIError(
                "INVALID_RESPONSE", "Wise API returned a non-JSON response"
            ) from None
        if not isinstance(payload, dict) or not isinstance(payload.get("meta"), dict):
            raise WiseAPIError("INVALID_RESPONSE", "Wise API response envelope is missing")
        meta = payload["meta"]
        if status >= 400 or meta.get("success") is not True:
            raise WiseAPIError(
                safe_text(meta.get("code"), token, "API_ERROR"),
                safe_text(meta.get("message"), token, "Wise rejected this request"),
                status=status if status >= 400 else 400,
            )
        if "data" not in payload:
            raise WiseAPIError("INVALID_RESPONSE", "Wise API response data is missing")
        return payload
