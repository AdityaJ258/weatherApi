"""
Thin async client around Open-Meteo's free geocoding + forecast APIs.
No API key, no billing, no rate-limit signup required -> keeps the whole
project at zero cost to run.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import httpx

from app.config import FORECAST_URL, GEOCODING_URL, WEATHER_USER_AGENT

WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class LocationNotFoundError(Exception):
    pass


async def geocode_location(location: str) -> dict[str, Any]:
    """Resolve a free-text place name to lat/lon + display name."""
    async with httpx.AsyncClient(
        headers={"User-Agent": WEATHER_USER_AGENT}, timeout=10
    ) as client:
        resp = await client.get(
            GEOCODING_URL, params={"name": location, "count": 1, "language": "en"}
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results") or []
    if not results:
        raise LocationNotFoundError(f"Could not find a location matching '{location}'")

    top = results[0]
    return {
        "name": top.get("name"),
        "country": top.get("country"),
        "latitude": top["latitude"],
        "longitude": top["longitude"],
        "timezone": top.get("timezone", "UTC"),
    }


async def fetch_current_weather(latitude: float, longitude: float, timezone: str = "auto") -> dict[str, Any]:
    """Fetch current conditions for a coordinate pair."""
    async with httpx.AsyncClient(
        headers={"User-Agent": WEATHER_USER_AGENT}, timeout=10
    ) as client:
        resp = await client.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "is_day,weather_code,wind_speed_10m,wind_direction_10m"
                ),
                "timezone": timezone,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_weather_for_location(location: str) -> dict[str, Any]:
    """
    High-level tool function: turns a place name into a fully structured
    current-weather reading. This is the function exposed as an MCP tool.
    """
    place = await geocode_location(location)
    raw = await fetch_current_weather(
        place["latitude"], place["longitude"], place.get("timezone", "auto")
    )
    current = raw.get("current", {})
    temp_c = current.get("temperature_2m")
    code = current.get("weather_code")

    return {
        "location_name": place["name"],
        "country": place.get("country"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "temperature_c": temp_c,
        "temperature_f": round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None,
        "feels_like_c": current.get("apparent_temperature"),
        "condition": WMO_CODES.get(code, "Unknown"),
        "humidity": current.get("relative_humidity_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "wind_direction_deg": current.get("wind_direction_10m"),
        "is_day": bool(current.get("is_day")),
        "observed_at": current.get("time") or dt.datetime.utcnow().isoformat(),
        "timezone": raw.get("timezone", "UTC"),
    }
