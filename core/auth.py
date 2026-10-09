"""Wise owns token validation; the MCP server does not issue or store credentials."""

from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token

from core.client import WiseAPIError, WiseClient


class WiseTokenVerifier(TokenVerifier):
    def __init__(self, client: WiseClient):
        super().__init__()
        self.client = client

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            result = await self.client.call("/user/", "get_me", token=token)
        except WiseAPIError:
            # Fail closed, without exposing upstream responses or caching revocations.
            return None
        user = result.get("data")
        if (
            not isinstance(user, dict)
            or not user.get("global_id")
            or user.get("is_active") is False
        ):
            return None
        return AccessToken(
            token=token, client_id="wise-public-mcp", subject=str(user["global_id"]), scopes=[]
        )


def caller_token() -> str:
    access = get_access_token()
    if access is None:
        raise ToolError("Connect using Authorization: Bearer <your Wise API token>.")
    return access.token
