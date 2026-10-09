import hashlib
import hmac
import json
from unittest.mock import patch

import httpx
import pytest

from core.client import WiseClient
from core.config import Settings
from core.signing import MCPRequestSigner
from tests.conftest import envelope

NOW = 1791547200
TEST_SECRET = "ab" * 32


def assert_signed(request):
    timestamp = request.headers["x-wise-mcp-timestamp"]
    payload = json.dumps(
        [
            "wise-mcp-v1",
            request.method,
            request.url.raw_path.decode("ascii"),
            request.headers["content-type"].lower(),
            timestamp,
            hashlib.sha256(request.content).hexdigest(),
            hashlib.sha256(request.headers["authorization"].encode()).hexdigest(),
        ],
        separators=(",", ":"),
    ).encode("ascii")
    expected = "v1=" + hmac.new(bytes.fromhex(TEST_SECRET), payload, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(request.headers["x-wise-mcp-signature"], expected)
    assert TEST_SECRET not in str(request.headers)
    assert "x-wise-mcp-nonce" not in request.headers


def test_fixed_contract_vector():
    request = httpx.Request(
        "POST",
        "https://api.example/api/ad/?view=public",
        content=b"method=get_ads&query=%D8%A2%D8%B2%D9%85%D8%A7%DB%8C%D8%B4&archived=false",
        headers={
            "Authorization": "Bearer contract-token",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with patch("core.signing.time.time", return_value=NOW):
        signed = next(MCPRequestSigner(TEST_SECRET).auth_flow(request))
    assert signed.headers["x-wise-mcp-signature"] == (
        "v1=543b5ce9c01a0736f1c60df81121e1ea69286e81ff2e98f227c7d93d1a07ab4c"
    )
    assert_signed(signed)


async def test_signs_actual_encoded_body_and_refreshes_timestamp(settings):
    requests = []

    def backend(request):
        assert_signed(request)
        requests.append(request)
        return httpx.Response(200, json=envelope([]))

    client = WiseClient(settings, transport=httpx.MockTransport(backend))
    with patch("core.signing.time.time", return_value=NOW) as clock:
        await client.call("/ad/", "get_ads", token="alice", params={"query": "آزمایش + &"})
        clock.return_value = NOW + 10
        await client.call("/ad/", "get_ads", token="bob", params={"query": "آزمایش + &"})
    assert [r.headers["x-wise-mcp-timestamp"] for r in requests] == [str(NOW), str(NOW + 10)]
    assert (
        requests[0].headers["x-wise-mcp-signature"] != requests[1].headers["x-wise-mcp-signature"]
    )


def test_missing_or_invalid_secret_fails_closed_without_exposing_it(monkeypatch):
    monkeypatch.delenv("WISE_MCP_SIGNING_SECRET")
    with pytest.raises(ValueError):
        Settings(_env_file=None)
    secret = "private-test-key-that-must-not-appear"
    with pytest.raises(ValueError) as error:
        Settings(_env_file=None, mcp_signing_secret=secret)
    assert secret not in str(error.value)
    settings = Settings(_env_file=None, mcp_signing_secret=TEST_SECRET)
    assert TEST_SECRET not in repr(settings)
