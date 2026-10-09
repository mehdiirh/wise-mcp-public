"""Reviewed public read operations; parameter descriptions follow the public collection."""

from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Current Language")
    async def get_current_language() -> ToolResult:
        """Retrieves the currently active language."""
        return await call_backend(
            client, "/i18n/", "get_current_language", title="Get Current Language", view="details"
        )

    @read_tool(mcp, title="Get Languages")
    async def get_languages() -> ToolResult:
        """Retrieves a list of supported languages."""
        return await call_backend(
            client, "/i18n/", "get_languages", title="Get Languages", view="details"
        )
