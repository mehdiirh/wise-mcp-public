"""Reviewed public read operations; parameter descriptions follow the public collection."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.tools import ToolResult
from pydantic import Field

from core.client import WiseClient
from services import call_backend, read_tool


def register(mcp: FastMCP, client: WiseClient) -> None:

    @read_tool(mcp, title="Get Coins Price")
    async def get_coins_price(
        amount: Annotated[int, Field(ge=1000)],
        currencies: Annotated[str, Field(pattern=r"^\w{3,4}(?:;\w{3,4})*$")],
        deduct_balance: bool = False,
    ) -> ToolResult:
        """Get the price of the coins in the specified currencies. Quote only. deduct_balance
        subtracts existing balance from the quoted amount; it does not debit any funds.

        Args:
            amount: The number of coins to get the price for.
            currencies: semicolon-separated currency codes to get the price in.
            deduct_balance: Whether to deduct user's balance from amount.
        """
        return await call_backend(
            client,
            "/payment/",
            "get_coins_price",
            title="Get Coins Price",
            view="table",
            amount=amount,
            currencies=currencies,
            deduct_balance=deduct_balance,
        )

    @read_tool(mcp, title="Get Currency Restrictions")
    async def get_currency_restrictions() -> ToolResult:
        """Retrieves a list of active currency restrictions for the authenticated user."""
        return await call_backend(
            client,
            "/payment/",
            "get_currency_restrictions",
            title="Get Currency Restrictions",
            view="table",
        )
