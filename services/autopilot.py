"""Reviewed public read operations; parameter descriptions follow the public collection."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import Field

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Autopilot")
    async def get_autopilot(ad_code: str) -> ToolResult:
        """Retrieves Autopilot availability, the current policy, and the latest stored observation
        for an ad.
        This endpoint does not fetch fresh Telegram data.

        Args:
            ad_code: The code of the ad to retrieve.
        """
        return await call_backend(
            client,
            "/autopilot/",
            "get_autopilot",
            title="Get Autopilot",
            view="details",
            ad_code=ad_code,
        )

    @read_tool(mcp, title="Get Autopilot Events")
    async def get_autopilot_events(
        ad_code: str,
        page: Annotated[int, Field(ge=1)] = 1,
        limit: Annotated[int, Field(ge=10, le=100)] = 25,
    ) -> ToolResult:
        """Retrieves a paginated history of Autopilot decisions and monitoring events, ordered
        newest first.

        Args:
            ad_code: The code of the ad whose events should be retrieved.
            page: Page number, starting at 1 (default 1). Values beyond the last page return the
            last page.
            limit: Number of events per page (default 25). Values are clamped to the range 10 to
            100.
        """
        return await call_backend(
            client,
            "/autopilot/",
            "get_autopilot_events",
            title="Get Autopilot Events",
            view="table",
            ad_code=ad_code,
            page=page,
            limit=limit,
        )
