"""Shared fixtures for all tests."""
import json
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def london_payload() -> dict:
    """A real Open-Meteo response for London, trimmed to 6 hours."""
    path = Path(__file__).parent / "fixtures" / "open_meteo_london.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def wmo() -> pd.DataFrame:
    """A small WMO code lookup table."""
    return pd.DataFrame({
        "code": [0, 3, 61, 71, 95],
        "description": ["Clear sky", "Overcast", "Slight rain", "Slight snow fall", "Thunderstorm"],
        "category": ["clear", "cloudy", "rain", "snow", "storm"],
    })


@pytest.fixture
def dq_cfg() -> dict:
    """Data quality thresholds used in tests."""
    return {
        "temperature_min_c": -30,
        "temperature_max_c": 45,
        "humidity_min_pct": 0,
        "humidity_max_pct": 100,
        "max_feels_like_gap_c": 15,
        "max_data_age_hours": 3,
        "min_hours_per_city": 4,
    }


@pytest.fixture
def clean_df() -> pd.DataFrame:
    """Six clean hourly rows for London, ready for validation."""
    times = pd.date_range("2026-11-10 00:00", periods=6, freq="h", tz="UTC")
    return pd.DataFrame({
        "city": "London",
        "observed_at_utc": times,
        "temperature_c": [5.0, 5.5, 6.0, 6.5, 7.0, 7.5],
        "feels_like_c": [3.0] * 6,
        "humidity_pct": [80] * 6,
        "precipitation_mm": [0.0] * 6,
        "wind_speed_kmh": [10.0] * 6,
        "weather_description": ["Overcast"] * 6,
    })
    