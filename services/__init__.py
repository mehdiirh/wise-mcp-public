"""Shared registration and results, following tgads-mcp's services.register pattern."""

import json
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult

from core.auth import caller_token
from core.client import WiseAPIError, WiseClient

UI_URI = "ui://wise-public/results.html"
READ_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def read_tool(mcp: FastMCP, *, title: str, visual: bool = True):
    return mcp.tool(
        title=title,
        annotations=READ_ANNOTATIONS,
        app={"resourceUri": UI_URI} if visual else None,
        output_schema={
            "type": "object",
            "required": ["data", "meta"],
            "properties": {
                "data": {"description": "Wise response data, or inline CSV when requested."},
                "extra": {"description": "Additional API metadata; format=csv for CSV responses."},
                "meta": {
                    "type": "object",
                    "required": ["success", "status"],
                    "properties": {
                        "success": {"type": "boolean"},
                        "status": {"type": "integer"},
                        "pagination": {
                            "type": ["object", "null"],
                            "description": "total counts records; page_range lists page numbers.",
                        },
                    },
                },
            },
        },
    )


async def call_backend(
    client: WiseClient, route: str, action: str, *, title: str, view: str = "details", **params: Any
) -> ToolResult:
    try:
        payload = await client.call(route, action, token=caller_token(), params=params)
    except WiseAPIError as error:
        raise ToolError(str(error)) from None
    return ToolResult(
        content=json.dumps(payload, ensure_ascii=False),
        structured_content=payload,
        meta={"wise/view": view, "wise/title": title, "wise/action": action},
    )
