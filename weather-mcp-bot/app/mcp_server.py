"""
This is a real MCP (Model Context Protocol) server. It exposes exactly one
tool -- get_weather -- over stdio, using the official `mcp` Python SDK's
FastMCP helper. The FastAPI app (app/mcp_client.py) talks to this process
as an MCP client, exactly the way any MCP-compatible host (Claude Desktop,
an IDE, etc.) would.

Run it standalone to test with the MCP dev inspector:
    mcp dev app/mcp_server.py

It is launched automatically as a subprocess by the FastAPI app at startup.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.weather_tool import LocationNotFoundError, get_weather_for_location

mcp = FastMCP("weather-tools")


@mcp.tool()
async def get_weather(location: str) -> dict:
    """
    Get the current weather (temperature, condition, humidity, wind) for a
    named place on Earth (city, town, or region name).

    Args:
        location: Free-text place name, e.g. "Tokyo", "Bhadravati, Maharashtra",
                  "Paris, France".
    """
    try:
        return await get_weather_for_location(location)
    except LocationNotFoundError as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    mcp.run()
