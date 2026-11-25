"""Unit tests for the per-source normalisers."""
import json
from pathlib import Path

import pandas as pd

from weatherflow.normalise import CANONICAL, normalise_open_meteo, normalise_weatherapi

FIXTURES = Path(__file__).parent / "fixtures"
CODES = pd.DataFrame({
    "code": [1009, 1183],
    "description": ["Overcast", "Light rain"],
    "category": ["cloudy", "rain"],
})


def weatherapi_payload() -> dict:
    """The trimmed WeatherAPI fixture (it contains no API key)."""
    return json.loads((FIXTURES / "weatherapi_london.json").read_text(encoding="utf-8"))


def test_open_meteo_is_normalised_to_canonical_columns(london_payload):
    out = normalise_open_meteo(london_payload, "London")
    assert list(out.columns) == CANONICAL
    assert len(out) == 6


def test_weatherapi_is_normalised_to_canonical_columns():
    out = normalise_weatherapi(weatherapi_payload(), "London", CODES)
    assert list(out.columns) == CANONICAL
    assert len(out) == 3


def test_weatherapi_time_comes_from_the_epoch_in_utc():
    out = normalise_weatherapi(weatherapi_payload(), "London", CODES)
    first = out.loc[0, "observed_at_utc"]
    assert str(first.tz) == "UTC"
    assert int(first.timestamp()) == 1795564800


def test_weatherapi_units_map_to_canonical_names():
    out = normalise_weatherapi(weatherapi_payload(), "London", CODES)
    assert out.loc[0, "temperature_c"] == 5.0
    assert out.loc[0, "wind_speed_kmh"] == 12.0
    assert out.loc[1, "precipitation_mm"] == 0.2


def test_weatherapi_condition_codes_map_to_wmo_style_codes():
    out = normalise_weatherapi(weatherapi_payload(), "London", CODES)
    assert out.loc[0, "weather_code"] == 3    # overcast -> cloudy
    assert out.loc[1, "weather_code"] == 61   # light rain -> rain


def test_unknown_weatherapi_condition_code_does_not_crash():
    out = normalise_weatherapi(weatherapi_payload(), "London", CODES)
    assert out.loc[2, "weather_code"] == -1


def test_weatherapi_daylight_flag_is_a_boolean():
    out = normalise_weatherapi(weatherapi_payload(), "London", CODES)
    assert out["is_daylight"].tolist() == [False, False, False]