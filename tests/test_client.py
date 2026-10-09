from urllib.parse import parse_qs

import httpx
import pytest

from core.auth import WiseTokenVerifier
from core.client import WiseAPIError, WiseClient
from core.config import Settings
from tests.conftest import EXCLUDED, envelope


@pytest.mark.parametrize("entry", EXCLUDED, ids=lambda p: p["action"])
async def test_every_excluded_public_action_is_blocked_before_network(settings, entry):
    def forbidden(_request):
        pytest.fail("Excluded action made a network call")

    client = WiseClient(settings, transport=httpx.MockTransport(forbidden))
    with pytest.raises(ValueError, match="allowlist"):
        await client.call(entry["route"], entry["action"], token="token")


@pytest.mark.parametrize("params", [{"method": "delete_ad"}, {"user_id": 42}, {"account_id": 1}])
async def test_privileged_or_override_parameters_blocked(settings, params):
    with pytest.raises(ValueError, match="parameters"):
        await WiseClient(settings).call("/ad/", "get_ads", token="token", params=params)


async def test_form_encoding_and_no_cookie_persistence(settings):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=envelope([]), headers={"Set-Cookie": "session=secret"})

    client = WiseClient(settings, transport=httpx.MockTransport(handler))
    for token in ("alice", "bob"):
        await client.call(
            "/ad/", "get_ads", token=token, params={"archived": False, "query": None, "page": 2}
        )
    for request, token in zip(requests, ("alice", "bob"), strict=True):
        assert str(request.url) == "https://api.example.test/api/ad/"
        assert request.headers["authorization"] == f"Bearer {token}"
        assert "cookie" not in request.headers
        assert parse_qs(request.content.decode()) == {
            "method": ["get_ads"],
            "archived": ["false"],
            "page": ["2"],
        }


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(302, headers={"Location": "https://evil.invalid"}), "UPSTREAM_REDIRECT"),
        (httpx.Response(429), "RATE_LIMITED"),
        (httpx.Response(500, text="backend secrets"), "UPSTREAM_UNAVAILABLE"),
        (httpx.Response(200, text="<html>error</html>"), "INVALID_RESPONSE"),
        (httpx.Response(200, json={"data": []}), "INVALID_RESPONSE"),
        (
            httpx.Response(200, json=envelope(success=False, code="DENIED", message="No access")),
            "DENIED",
        ),
        (
            httpx.Response(400, json=envelope(success=False, code="AUTHORIZATION_FAILED")),
            "AUTHORIZATION_FAILED",
        ),
    ],
)
async def test_api_failures_are_not_successful_tool_data(settings, response, code):
    client = WiseClient(settings, transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(WiseAPIError) as error:
        await client.call("/user/", "get_me", token="token")
    assert error.value.code == code
    assert "backend secrets" not in str(error.value)


async def test_size_limit_timeout_csv_and_secret_redaction(settings):
    settings.max_response_bytes = 1024

    async def call(response, **kwargs):
        client = WiseClient(settings, transport=httpx.MockTransport(lambda _: response))
        return await client.call("/stats/ad/", "get_daily_ad_stats", token="secret-token", **kwargs)

    with pytest.raises(WiseAPIError, match="RESPONSE_TOO_LARGE"):
        await call(httpx.Response(200, content=b"a" * 1025))
    csv = "datetime,views,clicks,joins\n2026-10-01,10,2,1\n"
    result = await call(
        httpx.Response(200, text=csv, headers={"content-type": "text/csv"}),
        params={"ad_code": "abcd1234", "as_csv": True},
    )
    assert result["data"] == csv and result["extra"]["format"] == "csv"
    with pytest.raises(WiseAPIError) as error:
        await call(
            httpx.Response(
                400,
                json=envelope(
                    success=False, code="INVALID", message="secret-token Bearer some-other-token"
                ),
            )
        )
    assert "secret-token" not in str(error.value)
    assert "some-other-token" not in str(error.value)

    def timeout(_):
        raise httpx.ReadTimeout("secret-token")

    with pytest.raises(WiseAPIError, match="UPSTREAM_TIMEOUT"):
        await WiseClient(settings, transport=httpx.MockTransport(timeout)).call(
            "/user/", "get_me", token="secret-token"
        )


async def test_backend_token_validation_is_not_cached(settings):
    valid = True

    def handler(request):
        assert request.headers["authorization"] == "Bearer opaque-wise-token"
        assert parse_qs(request.content.decode()) == {"method": ["get_me"]}
        return (
            httpx.Response(200, json=envelope({"global_id": "user-1", "is_active": True}))
            if valid
            else httpx.Response(400, json=envelope(success=False))
        )

    verifier = WiseTokenVerifier(WiseClient(settings, transport=httpx.MockTransport(handler)))
    token = await verifier.verify_token("opaque-wise-token")
    assert token and token.token == "opaque-wise-token" and token.subject == "user-1"
    valid = False
    assert await verifier.verify_token("opaque-wise-token") is None


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@api.example/api",
        "https://api.example/?token=x",
        "file:///etc/passwd",
        "http://remote.example/api",
    ],
)
def test_unsafe_upstream_configuration_rejected(url):
    with pytest.raises(ValueError):
        Settings(_env_file=None, api_base_url=url)
