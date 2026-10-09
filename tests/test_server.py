import asyncio
import json
from urllib.parse import parse_qs

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastmcp import Client

from core.policy import READ_ACTIONS
from server import create_server
from services import UI_URI
from tests.conftest import INCLUDED, POLICY, ROOT, app_with_backend, envelope

HEADERS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25"}


async def rpc(client, method, params=None, token="alice", **kwargs):
    headers = {**HEADERS, **kwargs.pop("headers", {})}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return await client.post(
        "/wise-mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers=headers,
        **kwargs,
    )


def test_complete_documentation_audit():
    collection = json.loads((ROOT / "docs/public_collection.json").read_text())
    documented = {}
    for folder in collection["item"]:
        for item in folder["item"]:
            request = item["request"]
            fields = request["body"][request["body"]["mode"]]
            action = next(f["value"] for f in fields if f["key"] == "method")
            route = request["url"]["raw"].replace("{{base_url}}", "")
            documented[route, action] = {f["key"] for f in fields if f["key"] != "method"}
    assert len(POLICY) == len(documented)
    assert {(p["route"], p["action"]) for p in POLICY} == documented.keys()
    assert READ_ACTIONS.keys() == {(p["route"], p["action"]) for p in INCLUDED}
    for key, params in READ_ACTIONS.items():
        assert params == documented[key]


async def test_tool_schemas_annotations_and_ui_resource(settings):
    async with Client(create_server(settings)) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools} == {p["tool"] for p in INCLUDED}
        for tool in tools:
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.destructiveHint is False
            assert tool.meta["ui"]["resourceUri"] == UI_URI
            assert tool.inputSchema["additionalProperties"] is False
            assert (
                not {"token", "user_id", "account_id", "method"}
                & tool.inputSchema["properties"].keys()
            )
        resources = await client.read_resource(UI_URI)
        assert resources[0].mimeType == "text/html;profile=mcp-app"
        assert "ui/initialize" in resources[0].text
        assert "innerHTML" not in resources[0].text
        assert "fetch(" not in resources[0].text


async def test_http_auth_health_and_host_guards(settings):
    requests = []

    def handler(request):
        requests.append(request)
        if request.headers["authorization"] == "Bearer invalid":
            return httpx.Response(400, json=envelope(success=False, code="AUTHORIZATION_FAILED"))
        return httpx.Response(200, json=envelope({"global_id": "u1", "is_active": True}))

    app = app_with_backend(settings, handler)
    async with (
        LifespanManager(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client,
    ):
        assert (await client.get("/healthz")).status_code == 200
        for token in (None, "invalid"):
            assert (await rpc(client, "tools/list", token=token)).status_code == 401
        assert (await rpc(client, "tools/list")).status_code == 200
        assert (
            await rpc(client, "tools/list", headers={"Host": "evil.invalid"})
        ).status_code == 421
        assert (
            await rpc(client, "tools/list", headers={"Origin": "https://evil.invalid"})
        ).status_code == 403
        assert len(requests) == 2


@pytest.mark.parametrize("entry", INCLUDED, ids=lambda p: p["tool"])
async def test_all_tools_through_authenticated_http(settings, entry):
    requests = []

    def handler(request):
        assert request.headers["user-agent"] == "wise-mcp-public/1.0.0"
        action = parse_qs(request.content.decode())["method"][0]
        requests.append((str(request.url), action, request.headers["authorization"]))
        data = {"global_id": "u1", "is_active": True} if action == "get_me" else []
        return httpx.Response(200, json=envelope(data))

    args = {
        "ad_code": "abcd1234",
        "text_id": "template-id",
        "amount": 1000,
        "currencies": "USD;EUR",
        "code": "USD",
    }
    parameters = {
        k: v for k, v in args.items() if k in READ_ACTIONS[entry["route"], entry["action"]]
    }
    app = app_with_backend(settings, handler)
    async with (
        LifespanManager(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client,
    ):
        response = await rpc(client, "tools/call", {"name": entry["tool"], "arguments": parameters})
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        assert not result.get("isError"), result
        assert result["structuredContent"]["meta"]["success"] is True
        assert result["_meta"]["wise/action"] == entry["action"]
        assert requests[-1] == (
            settings.api_base_url + entry["route"],
            entry["action"],
            "Bearer alice",
        )


async def test_concurrent_users_cannot_leak_tokens_or_impersonate(settings):
    seen = []

    async def handler(request):
        await asyncio.sleep(0.001)
        assert "x-user-id" not in request.headers and "cookie" not in request.headers
        token = request.headers["authorization"].split()[1]
        seen.append(token)
        return httpx.Response(200, json=envelope({"global_id": token, "is_active": True}))

    app = app_with_backend(settings, handler)
    async with (
        LifespanManager(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client,
    ):
        results = await asyncio.gather(
            *[
                rpc(
                    client,
                    "tools/call",
                    {"name": "get_me", "arguments": {}},
                    token=token,
                    headers={"X-User-ID": "admin", "Cookie": "session=admin"},
                )
                for token in ("alice", "bob", "carol")
            ]
        )
        assert [r.json()["result"]["structuredContent"]["data"]["global_id"] for r in results] == [
            "alice",
            "bob",
            "carol",
        ]
        assert sorted(seen) == ["alice", "alice", "bob", "bob", "carol", "carol"]


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("delete_ad", {"ad_code": "abcd1234"}),
        ("get_ads", {"user_id": 1}),
        ("get_ads", {"method": "delete_ad"}),
        ("get_ads", {"archived": "false"}),
        ("get_ads", {"page": 0}),
        ("get_daily_ad_stats", {"ad_code": "abcd1234", "limit": 100}),
        ("get_coins_price", {"amount": 10, "currencies": "USD"}),
    ],
)
async def test_invalid_tools_and_parameters_never_reach_backend(settings, name, args):
    actions = []

    def handler(request):
        actions.append(parse_qs(request.content.decode())["method"][0])
        return httpx.Response(200, json=envelope({"global_id": "u1", "is_active": True}))

    app = app_with_backend(settings, handler)
    async with (
        LifespanManager(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client,
    ):
        response = await rpc(client, "tools/call", {"name": name, "arguments": args})
        body = response.json()
        assert "error" in body or body["result"]["isError"]
        assert actions == ["get_me"]
