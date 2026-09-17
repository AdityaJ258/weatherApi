"""
The agent layer. Responsibilities:

1. Guardrail: decide whether the user's message is actually a weather/
   temperature/climate question for a location on Earth. Anything else is
   politely refused -- the bot must not answer general questions.
2. Extract the target location from the message.
3. Call the weather tool (over MCP) to get live data.
4. Retrieve a relevant snippet from the local knowledge base (RAG) when the
   question also touches a weather *concept* (e.g. "what is humidity").
5. Generate a final natural-language reply, either via an LLM (if
   OPENAI_API_KEY is configured) or via a deterministic template (default,
   zero-cost path) -- and always return the same structured schema.
"""
from __future__ import annotations

import json
import re

from app.config import LLM_ENABLED, OPENAI_API_KEY, OPENAI_MODEL
from app.mcp_client import MCPWeatherClient
from app.rag import retrieve
from app.schemas import ChatResponse, WeatherData
from app.weather_tool import LocationNotFoundError

WEATHER_KEYWORDS = [
    "weather", "temperature", "temp ", "forecast", "rain", "raining", "rainy",
    "snow", "snowing", "storm", "thunder", "wind", "windy", "humid", "humidity",
    "sunny", "sun", "cloud", "cloudy", "overcast", "hot", "cold", "cool",
    "degrees", "climate", "fog", "foggy", "drizzle", "hail", "uv index",
    "dew point", "feels like", "chilly", "warm",
]

GREETING_PATTERNS = re.compile(r"^\s*(hi|hello|hey|namaste|hola)[\s!.]*$", re.I)

LOCATION_PATTERNS = [
    re.compile(r"\b(?:weather|temperature|forecast|climate)\s+(?:in|at|for)\s+([A-Za-z .,'-]+?)(?:[?.!]|$)", re.I),
    re.compile(r"\b(?:in|at|for)\s+([A-Za-z .,'-]+?)(?:[?.!]|$)", re.I),
    re.compile(r"^([A-Za-z .,'-]+?)\s+(?:weather|temperature|forecast)\b", re.I),
]

SYSTEM_PROMPT = (
    "You are a weather-only assistant. You are given live, verified weather "
    "data for one location (from a trusted API) and, optionally, a short "
    "educational snippet about a weather concept. Write a concise, friendly "
    "1-3 sentence answer to the user's question using ONLY that data -- do "
    "not invent numbers. If a knowledge snippet is provided and the user's "
    "question relates to it, weave in a brief explanation. Do not discuss "
    "anything outside weather."
)


def is_weather_query(message: str) -> bool:
    lowered = message.lower()
    if GREETING_PATTERNS.match(message):
        return False
    return any(kw in lowered for kw in WEATHER_KEYWORDS)


def extract_location(message: str) -> str | None:
    for pattern in LOCATION_PATTERNS:
        match = pattern.search(message)
        if match:
            loc = match.group(1).strip(" ?.!,")
            if loc and loc.lower() not in {"today", "now", "here", "outside"}:
                return loc
    return None


def _template_reply(weather: dict, snippet: str | None) -> str:
    parts = [
        f"Right now in {weather['location_name']}"
        + (f", {weather['country']}" if weather.get("country") else "")
        + f": {weather['condition'].lower()}, "
        f"{weather['temperature_c']}°C (feels like {weather['feels_like_c']}°C)."
    ]
    if weather.get("humidity") is not None:
        parts.append(f"Humidity is {weather['humidity']}%.")
    if weather.get("wind_speed_kmh") is not None:
        parts.append(f"Wind speed is {weather['wind_speed_kmh']} km/h.")
    if snippet:
        parts.append(snippet)
    return " ".join(parts)


async def _llm_reply(user_message: str, weather: dict, snippet: str | None) -> str:
    from openai import AsyncOpenAI  # imported lazily so it's fully optional

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    context = {"weather_data": weather, "knowledge_snippet": snippet}
    resp = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User question: {user_message}\n\n"
                    f"Context JSON:\n{json.dumps(context)}"
                ),
            },
        ],
        temperature=0.4,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


async def handle_message(message: str, mcp_client: MCPWeatherClient) -> ChatResponse:
    if not is_weather_query(message):
        return ChatResponse(
            status="out_of_scope",
            reply=(
                "I can only help with weather and temperature questions for a "
                "place on Earth -- for example, \"What's the weather in Tokyo?\" "
                "or \"How humid is it in Mumbai right now?\""
            ),
        )

    location = extract_location(message)
    if not location:
        return ChatResponse(
            status="not_found",
            reply=(
                "Which location would you like the weather for? "
                "Try something like \"weather in Paris\"."
            ),
        )

    try:
        weather = await mcp_client.get_weather(location)
    except Exception as exc:  # noqa: BLE001
        return ChatResponse(status="error", reply=f"Sorry, something went wrong: {exc}")

    if "error" in weather:
        return ChatResponse(status="not_found", reply=weather["error"])

    snippet = retrieve(message)

    if LLM_ENABLED:
        try:
            reply_text = await _llm_reply(message, weather, snippet)
        except Exception:  # noqa: BLE001 -- fall back gracefully if LLM call fails
            reply_text = _template_reply(weather, snippet)
    else:
        reply_text = _template_reply(weather, snippet)

    return ChatResponse(
        status="ok",
        reply=reply_text,
        weather=WeatherData(**weather),
        knowledge_snippet=snippet,
    )
