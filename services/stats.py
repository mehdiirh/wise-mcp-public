"""Reviewed public read operations; parameter descriptions follow the public collection."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import Field

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Daily Ad Stats")
    async def get_daily_ad_stats(
        ad_code: str, limit: Annotated[int, Field(ge=7, le=60)] = 30, as_csv: bool = False
    ) -> ToolResult:
        """Get the statistics of an ad for the last `limit` days. Display the returned time series
        as a chart when the host supports MCP Apps. CSV is returned inline when as_csv is true.

        Args:
            ad_code: The code of the ad to get the statistics for
            limit: The number of days to get the statistics for (min: 7, max: 60, default: 30)
            as_csv: Request the stats as a CSV file
        """
        return await call_backend(
            client,
            "/stats/ad/",
            "get_daily_ad_stats",
            title="Get Daily Ad Stats",
            view="chart",
            ad_code=ad_code,
            limit=limit,
            as_csv=as_csv,
        )

    @read_tool(mcp, title="Get Hourly Ad Stats")
    async def get_hourly_ad_stats(
        ad_code: str, limit: Annotated[int, Field(ge=8, le=48)] = 24, as_csv: bool = False
    ) -> ToolResult:
        """Get the detailed (1-hour interval) statistics of an ad for the last `limit` hours.
        Display the returned time series as a chart when the host supports MCP Apps. CSV is returned
        inline when as_csv is true.

        Args:
            ad_code: The code of the ad to get the statistics for
            limit: The number of hours to get the statistics for (min: 8, max: 48, default: 24)
            as_csv: Request the stats as a CSV file
        """
        return await call_backend(
            client,
            "/stats/ad/",
            "get_hourly_ad_stats",
            title="Get Hourly Ad Stats",
            view="chart",
            ad_code=ad_code,
            limit=limit,
            as_csv=as_csv,
        )

    @read_tool(mcp, title="Get 5Min Ad Stats")
    async def get_5min_ad_stats(
        ad_code: str, limit: Annotated[int, Field(ge=8, le=48)] = 24, as_csv: bool = False
    ) -> ToolResult:
        """Get the detailed (5-minute interval) statistics of an ad for the last `limit` hours.
        Display the returned time series as a chart when the host supports MCP Apps. CSV is returned
        inline when as_csv is true.

        Args:
            ad_code: The code of the ad to get the statistics for
            limit: The number of hours to get the statistics for (min: 8, max: 48, default: 24)
            as_csv: Request the stats as a CSV file
        """
        return await call_backend(
            client,
            "/stats/ad/",
            "get_5min_ad_stats",
            title="Get 5Min Ad Stats",
            view="chart",
            ad_code=ad_code,
            limit=limit,
            as_csv=as_csv,
        )

    @read_tool(mcp, title="Get Sum Ad Stats")
    async def get_sum_ad_stats(limit: Annotated[int, Field(ge=7, le=60)] = 30) -> ToolResult:
        """Get the sum of stats for all ads in the last `limit` days. Display the returned time
        series as a chart when supported.

        Args:
            limit: The number of days to get the statistics for (min: 7, max: 60, default: 30)
        """
        return await call_backend(
            client,
            "/stats/ad/",
            "get_sum_ad_stats",
            title="Get Sum Ad Stats",
            view="chart",
            limit=limit,
        )

    @read_tool(mcp, title="Account summary")
    async def get_user_summary() -> ToolResult:
        """Get the summary of the user's statistics."""
        return await call_backend(
            client, "/stats/user/", "summary", title="Account summary", view="cards"
        )
