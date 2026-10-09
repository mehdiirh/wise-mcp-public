"""Reviewed public read operations; parameter descriptions follow the public collection."""

from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import Field

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Ads")
    async def get_ads(
        limit: Annotated[int, Field(ge=10, le=100)] = 50,
        page: Annotated[int, Field(ge=1)] = 1,
        archived: bool | None = None,
        status: Literal["IN_REVIEW", "ACTIVE", "STOPPED", "DECLINED"] | None = None,
        query: str | None = None,
    ) -> ToolResult:
        """Fetches a paginated list of ads.

        Args:
            limit: Number of ads per page (default 50).
            page: Page number to fetch (default 1).
            archived: whether to fetch archived ads (True), or not (False) or do not filter (None)
            status: status to filter, can be "IN_REVIEW", "ACTIVE", "STOPPED", "DECLINED"
            query: Search query to filter ads.
        """
        return await call_backend(
            client,
            "/ad/",
            "get_ads",
            title="Get Ads",
            view="table",
            limit=limit,
            page=page,
            archived=archived,
            status=status,
            query=query,
        )

    @read_tool(mcp, title="Get Ad")
    async def get_ad(ad_code: str) -> ToolResult:
        """Fetches details of a specific ad by its ID.

        Args:
            ad_code: The code of the ad to retrieve.
        """
        return await call_backend(
            client, "/ad/", "get_ad", title="Get Ad", view="details", ad_code=ad_code
        )

    @read_tool(mcp, title="Ad Transactions")
    async def ad_transactions(
        ad_code: str,
        limit: Annotated[int, Field(ge=10, le=100)] = 50,
        page: Annotated[int, Field(ge=1)] = 1,
    ) -> ToolResult:
        """Fetches a paginated list of transactions related to an ad.

        Args:
            ad_code: The code of the ad to retrieve transactions for.
            limit: Number of transactions per page (default 50).
            page: Page number to fetch (default 1).
        """
        return await call_backend(
            client,
            "/ad/",
            "ad_transactions",
            title="Ad Transactions",
            view="table",
            ad_code=ad_code,
            limit=limit,
            page=page,
        )

    @read_tool(mcp, title="Search Location")
    async def search_location(
        country_code: Annotated[str, Field(pattern=r"^[A-Z]{2}$")] | None = None,
        query: str | None = None,
    ) -> ToolResult:
        """Searches for locations within a country.

        Args:
            country_code: The two-letter country code to search in.
            query: An optional prefix used to filter location names.
        """
        return await call_backend(
            client,
            "/ad/",
            "search_location",
            title="Search Location",
            view="table",
            country_code=country_code,
            query=query,
        )
