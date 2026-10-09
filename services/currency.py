"""Reviewed public read operations; parameter descriptions follow the public collection."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import Field

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Currencies")
    async def get_currencies() -> ToolResult:
        """Retrieve all active currencies."""
        return await call_backend(
            client, "/currency/", "get_currencies", title="Get Currencies", view="table"
        )

    @read_tool(mcp, title="Get Currency")
    async def get_currency(code: Annotated[str, Field(min_length=3, max_length=3)]) -> ToolResult:
        """Retrieve a specific currency by its ISO code (case-insensitive).

        Args:
            code: ISO code of the currency
        """
        return await call_backend(
            client, "/currency/", "get_currency", title="Get Currency", view="details", code=code
        )
