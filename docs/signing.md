# Wise MCP origin signature v1

The MCP service and Wise backend share 32 random bytes, configured as the same
64-character hexadecimal `WISE_MCP_SIGNING_SECRET`. Users only provide their
normal Wise token. The secret is never included in requests or client responses.

For each fully encoded outgoing request, construct this ordered JSON array:

```text
[
  "wise-mcp-v1",
  uppercase HTTP method,
  ASCII path plus optional query string (no scheme or host),
  lowercase Content-Type header value,
  decimal Unix timestamp string,
  lowercase SHA-256 hex digest of the exact request body bytes,
  lowercase SHA-256 hex digest of the UTF-8 Authorization header value
]
```

Serialize using `json.dumps(values, separators=(",", ":"), ensure_ascii=True)`
and ASCII-encode it. HMAC-SHA256 this payload with the hex-decoded secret. Send:

```text
X-Wise-MCP-Timestamp: <timestamp string>
X-Wise-MCP-Signature: v1=<lowercase HMAC hex digest>
User-Agent: wise-mcp-public/1.0.0
Authorization: Bearer <user's Wise token>
```

The backend compares signatures in constant time and verifies
`-5 <= current_unix_time - timestamp <= 60`. A valid signature annotates the
request; API authorization still runs independently. An invalid signature is
unverified rather than an authentication failure. There is no nonce or replay
cache. Identical captured requests are reusable within the window.

The path includes the API mount prefix and query string in wire order. The MCP
signer uses HTTPX's `url.raw_path`; Django verifies `request.get_full_path()`.
Current allowlisted API paths are fixed ASCII routes. Proxies must not rewrite
the signed target or body. Distinct trusted environments should use distinct
keys because the hostname is not part of this contract.

The MCP signer tests this fixed contract vector (the key is synthetic):

```text
key hex: ab repeated 32 times
method: POST
target: /api/ad/?view=public
content type: application/x-www-form-urlencoded
timestamp: 1791547200
body: method=get_ads&query=%D8%A2%D8%B2%D9%85%D8%A7%DB%8C%D8%B4&archived=false
authorization: Bearer contract-token
signature: v1=543b5ce9c01a0736f1c60df81121e1ea69286e81ff2e98f227c7d93d1a07ab4c
```

Version changes must update both implementations and the MCP contract tests.
