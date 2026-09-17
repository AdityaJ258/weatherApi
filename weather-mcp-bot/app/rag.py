"""
A small, self-contained RAG (retrieval-augmented generation) component.

Rather than depending on a paid vector DB or embeddings API, this keeps a
short curated knowledge base of weather concepts in memory and retrieves
the most relevant snippet with a TF-IDF + cosine-similarity index
(scikit-learn), which runs instantly and offline. The retrieved snippet is
passed into the agent's response generation step to ground/augment answers
that touch on weather *concepts* (e.g. "what does humidity mean"),
alongside the live tool data.
"""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KNOWLEDGE_BASE: list[dict[str, str]] = [
    {
        "topic": "humidity",
        "text": (
            "Relative humidity is the amount of water vapor in the air compared "
            "to the maximum it could hold at that temperature, shown as a "
            "percentage. High humidity makes hot weather feel hotter because "
            "sweat evaporates more slowly."
        ),
    },
    {
        "topic": "feels_like / apparent temperature",
        "text": (
            "'Feels like' (apparent) temperature adjusts the actual air "
            "temperature for wind chill in cold weather and humidity in hot "
            "weather, to approximate what the body actually experiences."
        ),
    },
    {
        "topic": "wind speed and direction",
        "text": (
            "Wind speed is usually reported in km/h or mph at 10 meters above "
            "ground. Wind direction is given in degrees, where 0/360 is north, "
            "90 is east, 180 is south, and 270 is west, indicating where the "
            "wind is blowing FROM."
        ),
    },
    {
        "topic": "weather codes / conditions",
        "text": (
            "Weather conditions such as 'clear sky', 'overcast', 'drizzle', or "
            "'thunderstorm' come from the WMO (World Meteorological "
            "Organization) weather interpretation codes, a standardized scale "
            "used by meteorological services worldwide."
        ),
    },
    {
        "topic": "forecast vs current conditions",
        "text": (
            "Current conditions describe the weather right now at a location, "
            "measured or modeled for the present moment, whereas a forecast "
            "predicts conditions at a future time using atmospheric models."
        ),
    },
    {
        "topic": "temperature units",
        "text": (
            "Temperature is commonly reported in Celsius (used by most of the "
            "world) or Fahrenheit (used mainly in the US). To convert Celsius "
            "to Fahrenheit: multiply by 9/5 and add 32."
        ),
    },
    {
        "topic": "dew point",
        "text": (
            "Dew point is the temperature air would need to cool to in order "
            "to become saturated with moisture and form dew. A higher dew "
            "point means muggier, more uncomfortable air."
        ),
    },
    {
        "topic": "UV index",
        "text": (
            "The UV index measures the strength of sunburn-producing "
            "ultraviolet radiation at a location. Values of 0-2 are low risk, "
            "3-5 moderate, 6-7 high, 8-10 very high, and 11+ extreme."
        ),
    },
]

_texts = [doc["text"] for doc in KNOWLEDGE_BASE]
_vectorizer = TfidfVectorizer(stop_words="english")
_matrix = _vectorizer.fit_transform(_texts)


def retrieve(query: str, min_score: float = 0.12) -> str | None:
    """Return the single best-matching knowledge snippet for a query, or None."""
    query_vec = _vectorizer.transform([query])
    scores = cosine_similarity(query_vec, _matrix).flatten()
    best_idx = scores.argmax()
    if scores[best_idx] < min_score:
        return None
    return KNOWLEDGE_BASE[best_idx]["text"]
