"""
Manages a single long-lived MCP ClientSession, connected over stdio to
app/mcp_server.py (spawned as a subprocess). FastAPI opens this once at
startup (see app/main.py lifespan) and reuses it for every chat request,
rather than paying subprocess-startup cost per request.
"""
from __future__ import annotations

import contextlib
import json
import sys
from typing import Any, AsyncIterator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPWeatherClient:
    def __init__(self) -> None:
        self._exit_stack = contextlib.AsyncExitStack()
        self.session: ClientSession | None = None

    async def start(self) -> None:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
        )
        read, write = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()

    async def stop(self) -> None:
        await self._exit_stack.aclose()
        self.session = None

    async def get_weather(self, location: str) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("MCP session not started")
        result = await self.session.call_tool("get_weather", {"location": location})
        # MCP tool results come back as a list of content blocks; the
        # FastMCP tool returns a dict, which arrives as a JSON text block.
        for block in result.content:
            if block.type == "text":
                return json.loads(block.text)
        raise RuntimeError("Unexpected MCP tool response shape")
