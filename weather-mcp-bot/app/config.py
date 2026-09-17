"""
Central configuration. Everything here works with zero paid dependencies:
- Weather + geocoding data comes from Open-Meteo, which is free and requires
  no API key at all (https://open-meteo.com).
- OPENAI_API_KEY is entirely optional. If it's not set, the agent falls back
  to a deterministic, template-based response generator so the whole app
  still works (and still costs nothing) without any LLM key.
"""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY") or None
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
WEATHER_USER_AGENT: str = os.getenv(
    "WEATHER_USER_AGENT", "weather-mcp-bot/1.0 (contact@example.com)"
)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

LLM_ENABLED: bool = OPENAI_API_KEY is not None
