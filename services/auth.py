"""Reviewed public read operations; parameter descriptions follow the public collection."""

from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Geolocation")
    async def get_geolocation() -> ToolResult:
        """Returns the geolocation of the user based on their IP address. This describes the MCP
        server egress IP, not the end user device; client IP headers are never forwarded."""
        return await call_backend(
            client, "/user/auth/", "get_geolocation", title="Get Geolocation", view="details"
        )
