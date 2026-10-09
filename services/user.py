"""Reviewed public read operations; parameter descriptions follow the public collection."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import Field

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Me")
    async def get_me() -> ToolResult:
        """Retrieves information about the currently authenticated user, including Autopilot beta
        access and welcome acknowledgment."""
        return await call_backend(client, "/user/", "get_me", title="Get Me", view="cards")

    @read_tool(mcp, title="Get User Payments")
    async def get_user_payments(
        payment_statuses: str | None = None,
        limit: Annotated[int, Field(ge=10, le=100)] = 50,
        page: Annotated[int, Field(ge=1)] = 1,
    ) -> ToolResult:
        """Retrieves a paginated list of payments made by the user.

        Args:
            payment_statuses: semicolon-separated list of payment statuses to filter by.
            limit: The number of payments to retrieve per page (default 50).
            page: The page number to retrieve (default 1).
        """
        return await call_backend(
            client,
            "/user/",
            "get_user_payments",
            title="Get User Payments",
            view="table",
            payment_statuses=payment_statuses,
            limit=limit,
            page=page,
        )

    @read_tool(mcp, title="Referral Stats")
    async def referral_stats() -> ToolResult:
        """Retrieves the referral statistics for the authenticated user."""
        return await call_backend(
            client, "/user/", "referral_stats", title="Referral Stats", view="cards"
        )
