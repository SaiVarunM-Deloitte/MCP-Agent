from __future__ import annotations

import json
from typing import Any


class PlaywrightExecutor:
    """
    Thin wrapper around the MCP ClientSession.

    The AI agent calls MCP tools through this class.
    """

    def __init__(self, session):
        self.session = session

    async def list_tools(self):
        """
        Return all tools exposed by Playwright MCP.
        """
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:

        arguments = arguments or {}

        print(
            f"\n[MCP] {tool_name}"
            f" {json.dumps(arguments, default=str)}"
        )

        result = await self.session.call_tool(
            tool_name,
            arguments
        )

        return result

    async def navigate(self, url: str):
        return await self.call_tool(
            "browser_navigate",
            {"url": url}
        )

    async def snapshot(self):
        return await self.call_tool(
            "browser_snapshot",
            {}
        )