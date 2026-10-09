# Wise Public MCP

A standalone, read-only MCP server for the **Wise advertising API** at
[docs.wise.ad](https://docs.wise.ad/). Uses `uv`, Python 3.12, FastMCP, and the
`server.py` / `core/` / `services/` layout of `tgads-mcp`.

## Start with Docker

```sh
cp sample.env .env
docker compose up --build -d
curl --fail http://127.0.0.1:8080/healthz
```

Defaults work against `https://api.wise.ad/api`. No shared API key or MCP secret
is needed. Each client supplies its **own Wise token** in the connection's
`Authorization: Bearer <WISE_TOKEN>` header.

- MCP URL: `http://127.0.0.1:8080/wise-mcp`
- Transport: Streamable HTTP (stateless, JSON responses)
- Health: `/healthz` (unauthenticated liveness only; does not call Wise)

The image runs as UID 10001, with a read-only filesystem, dropped capabilities,
and a health check. Dependencies are installed from `uv.lock`; the runtime image
does not contain development tools, tokens, documentation snapshots, or tests.
Compose binds only to loopback. It requires Compose 2.24+ for optional env files.

Standalone Docker:

```sh
docker build -t wise-mcp-public:1.0.0 .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp --env-file .env -p 127.0.0.1:8080:8000 wise-mcp-public:1.0.0
```

## Run with uv

```sh
uv sync --frozen
uv run python server.py
```

The local default port is 8000, or `WISE_PORT` from `.env`. The application also
exports `server:asgi_application` for ASGI deployments. No backend checkout,
Django installation, database, or Node build is required.

## Connect an assistant

Use a client that supports Streamable HTTP and bearer authentication. Configure
the token in the client's secure connection settings, not in chat, URLs, tool
arguments, or this project's `.env`. The server does not implement OAuth login
or issue tokens; OAuth-only connectors need a separate compatible integration.

Clients using the common `mcpServers` configuration can use this shape (header
and secret-storage syntax varies by client):

```json
{
  "mcpServers": {
    "wise-public": {
      "url": "http://127.0.0.1:8080/wise-mcp",
      "headers": {"Authorization": "Bearer <your Wise token>"}
    }
  }
}
```

Python connection example; `WISE_TOKEN` here is a **client-side** environment
variable and is never a server-wide fallback:

```python
import asyncio
import os
from fastmcp import Client


async def main():
    async with Client("http://127.0.0.1:8080/wise-mcp", auth=os.environ["WISE_TOKEN"]) as client:
        result = await client.call_tool("get_user_summary", {})
        print(result.structured_content)


asyncio.run(main())
```

On every authenticated MCP HTTP request, the server sends the exact supplied
token to Wise's public `get_me` action. Wise validates it and determines the
user. Each tool forwards that same request-scoped token again for backend
authorization. Tokens and results are not cached. Invalid/revoked tokens fail
closed; if Wise cannot validate a token during an outage, authentication also
fails closed. There is no local token database, shared admin key, user-ID
impersonation, cookie forwarding, or session credential reuse.

Every backend request, including `get_me` token validation, sends
`User-Agent: wise-mcp-public/1.0.0` so Wise can identify MCP-originated requests.

## Read-only boundary

Wise uses **POST with a form-encoded `method` field even for reads**. Read-only
is enforced by a reviewed allowlist of exact `(route, method)` pairs and their
public parameters, not by the HTTP verb or a `get_` name prefix. There is no
generic request tool. Unknown parameters and staff selectors are rejected.
Redirects are never followed, keeping bearer tokens on the configured API origin.

All 52 actions in the public collection were classified; 23 are included.
[`docs/endpoint-policy.json`](docs/endpoint-policy.json) explains every decision.
The public collection was downloaded from
[`/collection.json`](https://docs.wise.ad/collection.json) on 2026-10-09 and
checked against the available backend implementation. The snapshot is only
documentation/test evidence: runtime never discovers or enables new actions.

| Area | Tools |
| --- | --- |
| Account | `get_me`, `get_user_summary`, `referral_stats` |
| Advertisements | `get_ads`, `get_ad`, `ad_transactions`, `search_location` |
| Statistics | `get_daily_ad_stats`, `get_hourly_ad_stats`, `get_5min_ad_stats`, `get_sum_ad_stats` |
| Payments and quotes | `get_user_payments`, `get_coins_price`, `get_currency_restrictions` |
| Currencies | `get_currencies`, `get_currency` |
| Templates | `get_ad_template`, `get_ad_templates` |
| Autopilot | `get_autopilot`, `get_autopilot_events` |
| Language | `get_languages`, `get_current_language` |
| Connection geography | `get_geolocation` |

Excluded: creating/editing/deleting/archiving ads or templates, changing balances,
transfers, review submission, media uploads, AI generation, prepared messages,
login/logout, language changes, and Autopilot configuration/resume/execution.
Also excluded even though they look like reads: `search_channel`, `search_bot`,
`search_target_query`, `get_custom_emoji`, `get_similar_channels`,
`get_similar_bots`, and `check_ad_post`; the current backend can create/update
stored entities while performing these lookups or validation.

The boundary covers application operations. Normal backend request logging,
infrastructure caches (including location lookup caching), and authentication
bookkeeping are controlled by Wise and cannot be disabled by an API client.
Permissions and object visibility remain exactly those enforced by Wise for the
supplied token; using a staff token does not downgrade its backend permissions.

## Responses and visual presentation

Tools return the Wise `{data, extra, meta}` envelope as both structured MCP
content and JSON text. API errors, timeouts, rate limiting, malformed responses,
and oversized responses become MCP tool errors. No automatic retries are made.
The full response, including null values and pagination, is preserved.

Every tool declares read-only annotations and a standard
[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) `ui://`
resource. Compatible hosts can render:

- Account and referral metric cards, with expandable nested details.
- Filterable and sortable ad, payment, template, currency, and event tables.
- Statistics charts with views/clicks/joins selectors and raw data inspection.
- Empty/error states and light/dark styling.

The UI ships inline HTML/CSS/JavaScript, uses no remote libraries, makes no API
calls, has no write controls, and never receives connection tokens. Returned
strings are inserted as text, not HTML. It verifies the parent message source
and pins the origin during the MCP Apps handshake. Hosts without MCP Apps still
receive complete text/structured results; UI rendering ultimately depends on
the host and cannot be forced by the server.

Pagination is explicit: `meta.pagination.total` counts **records**, not pages.
`page_range`, `current_page`, and `has_next` describe navigation. The UI filters
only the received page; ask the assistant to fetch another page when needed.
Page sizes are 10–100. Daily/aggregate statistics use 7–60 days; hourly and
five-minute statistics use 8–48 hours. The three per-ad statistics tools support
`as_csv=true`, returning CSV **inline**, without creating files or download URLs.
Prices and monetary strings retain backend precision; no conversion is inferred.
`deduct_balance` changes the quoted amount only and never debits funds.
`get_geolocation` describes the MCP server's egress IP, not the user's device.
Autopilot returns stored observations, without fetching fresh Telegram data.

Try asking: “Show my account summary”, “Compare my ad performance over 30 days”,
“List pending payments”, or “Show recent Autopilot decisions for ad ab123456”.

## Deployment configuration

| Setting | Default | Purpose |
| --- | --- | --- |
| `WISE_API_BASE_URL` | `https://api.wise.ad/api` | API root with mount prefix; HTTPS required except loopback development |
| `WISE_TIMEOUT_SECONDS` | `30` | Upstream request timeout |
| `WISE_MAX_RESPONSE_BYTES` | `4194304` | Maximum decoded response size |
| `WISE_HOST` | `0.0.0.0` | Listen address |
| `WISE_PORT` | `8000` | Listen port; Compose pins container port to 8000 |
| `WISE_ALLOWED_HOSTS` | `["localhost","127.0.0.1","[::1]"]` | JSON array of permitted MCP Host names |
| `MCP_PORT` | `8080` | Compose host port only |

For remote access, put an HTTPS reverse proxy in front of the loopback port,
add the exact public MCP hostname to `WISE_ALLOWED_HOSTS`, and preserve the
`Authorization` header. Do not log authorization headers or query-string
credentials. For an existing Nginx TLS virtual host:

```nginx
location /wise-mcp {
    proxy_pass http://127.0.0.1:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Authorization $http_authorization;
    proxy_buffering off;
    proxy_read_timeout 90s;
}
```

TLS certificate and DNS setup are deployment-specific. No public hostname,
certificate, or production token is provisioned by this repository. `/healthz`
is liveness only; test backend access through `get_me` using your own connection.

## Development and checks

```sh
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/preview_ui.py
```

Open `http://127.0.0.1:8765` for synthetic cards, charts, tables, empty/error
states, and theme switching. The preview is loopback-only and needs no token.
Tests mock the upstream API but exercise authenticated HTTP MCP calls for all
23 tools, token isolation, input validation, write rejection, CSV handling,
response limits, errors, and documentation coverage. Do not add a method merely
because its name starts with `get`; review backend side effects and public
parameter visibility, update the policy, and add coverage first.

```text
server.py              # MCP setup, ASGI app, health check, UI resource
core/auth.py           # Backend token verification and request identity
core/client.py         # Bounded HTTP calls and errors
core/policy.py         # Exact read-only action/parameter allowlist
services/              # Typed tool functions grouped by Wise service
ui/results.html        # Self-contained MCP Apps result presentation
docs/                  # Public API snapshot and all endpoint decisions
tests/                 # Boundary, API, authentication, HTTP protocol tests
scripts/               # Synthetic local UI preview
Dockerfile             # Non-root multi-stage image
docker-compose.yml     # Hardened single-service deployment
uv.lock                # Reproducible dependencies
```

Container integration smoke test (synthetic users/backend, real HTTP, no live token):

```sh
docker build -t wise-mcp-public:1.0.0 .
docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp -v "$PWD/scripts/smoke_container.py:/smoke.py:ro" \
  wise-mcp-public:1.0.0 python /smoke.py
```
