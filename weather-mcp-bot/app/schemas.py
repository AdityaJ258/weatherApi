"""
All API responses are returned through these models so the shape of the
answer is always consistent, whether the query was in-scope, out-of-scope,
or failed.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class WeatherData(BaseModel):
    location_name: str
    country: Optional[str] = None
    latitude: float
    longitude: float
    temperature_c: float
    temperature_f: float
    feels_like_c: float
    condition: str
    humidity: Optional[int] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    is_day: Optional[bool] = None
    observed_at: str
    timezone: str


class ChatResponse(BaseModel):
    status: Literal["ok", "out_of_scope", "not_found", "error"]
    reply: str
    weather: Optional[WeatherData] = None
    knowledge_snippet: Optional[str] = None
    source: str = "Open-Meteo"
