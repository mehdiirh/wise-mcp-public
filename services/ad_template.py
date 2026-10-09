"""Reviewed public read operations; parameter descriptions follow the public collection."""

from fastmcp import FastMCP
from fastmcp.tools import ToolResult

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Ad template")
    async def get_ad_template(text_id: str) -> ToolResult:
        """Get an ad template object

        Args:
            text_id: global ID of the ad template to be retrieved.
        """
        return await call_backend(
            client,
            "/utils/ad_template/",
            "get",
            title="Ad template",
            view="details",
            text_id=text_id,
        )

    @read_tool(mcp, title="Ad templates")
    async def get_ad_templates() -> ToolResult:
        """Get all ad templates"""
        return await call_backend(
            client, "/utils/ad_template/", "get_all", title="Ad templates", view="table"
        )
