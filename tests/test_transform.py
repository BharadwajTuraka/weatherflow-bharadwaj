"""Unit tests for the pure transform functions."""
import pandas as pd
import pytest

from weatherflow.transform import (
    COLUMNS,
    add_derived_metrics,
    add_weather_description,
    deduplicate,
    flatten_payload,
    standardise_columns,
    transform,
)

INGESTED = "2026-11-18T09:00:00+00:00"


def make_row(temperature_c=10.0, wind_kmh=0.0, precip=0.0, category="cloudy") -> pd.DataFrame:
    """Build a one-row table with the columns add_derived_metrics needs."""
    return pd.DataFrame({
        "temperature_c": [temperature_c],
        "wind_speed_kmh": [wind_kmh],
        "precipitation_mm": [precip],
        "weather_category": [category],
    })


def test_flatten_payload_returns_one_row_per_hour(london_payload):
    df = flatten_payload(london_payload, "London")
    assert len(df) == 6
    assert {"time", "temperature_2m", "city"} <= set(df.columns)


def test_standardise_columns_renames_and_derives_london_time(london_payload):
    out = standardise_columns(flatten_payload(london_payload, "London"), ingested_at=INGESTED)
    assert {"observed_at_utc", "temperature_c", "is_daylight"} <= set(out.columns)
    assert str(out["observed_at_local"].dt.tz) == "Europe/London"
    assert (out["ingested_at_utc"] == INGESTED).all()


def test_unknown_weather_code_becomes_unknown(wmo):
    out = add_weather_description(pd.DataFrame({"weather_code": [3, 999]}), wmo)
    assert out["weather_description"].tolist() == ["Overcast", "unknown"]
    assert out["weather_category"].tolist() == ["cloudy", "unknown"]


def test_temperature_converts_to_fahrenheit():
    assert add_derived_metrics(make_row(temperature_c=100.0)).loc[0, "temperature_f"] == pytest.approx(212.0)
    assert add_derived_metrics(make_row(temperature_c=0.0)).loc[0, "temperature_f"] == pytest.approx(32.0)


def test_wind_converts_from_kmh_to_metres_per_second():
    assert add_derived_metrics(make_row(wind_kmh=36.0)).loc[0, "wind_speed_ms"] == pytest.approx(10.0)


@pytest.mark.parametrize(
    "wind_kmh, expected_force",
    [(0.0, 0), (1.0, 0), (3.6, 1), (18.0, 3), (36.0, 5), (49.9, 6), (50.1, 7), (120.0, 12)],
)
def test_beaufort_scale_maps_wind_to_the_right_force(wind_kmh, expected_force):
    assert add_derived_metrics(make_row(wind_kmh=wind_kmh)).loc[0, "beaufort_scale"] == expected_force


@pytest.mark.parametrize(
    "temperature_c, wind_kmh, precip, category, expected",
    [
        (10.0, 0.0, 0.0, "cloudy", "low"),
        (10.0, 25.0, 0.0, "clear", "low"),      # Beaufort 4
        (10.0, 30.0, 0.0, "clear", "medium"),   # Beaufort 5
        (10.0, 49.9, 0.0, "clear", "medium"),   # Beaufort 6, just below the Beaufort 7 threshold
        (10.0, 50.1, 0.0, "clear", "high"),     # Beaufort 7, just above it
        (10.0, 0.0, 0.9, "rain", "low"),
        (10.0, 0.0, 1.0, "rain", "medium"),     # exactly 1 mm
        (10.0, 0.0, 3.9, "rain", "medium"),
        (10.0, 0.0, 4.0, "rain", "high"),       # exactly 4 mm
        (0.1, 0.0, 0.0, "clear", "low"),
        (0.0, 0.0, 0.0, "clear", "medium"),     # exactly 0 C
        (-5.0, 0.0, 0.0, "clear", "medium"),
        (10.0, 0.0, 0.0, "storm", "high"),
        (10.0, 0.0, 0.0, "snow", "high"),
    ],
)
def test_outdoor_work_risk_follows_the_rules(temperature_c, wind_kmh, precip, category, expected):
    out = add_derived_metrics(make_row(temperature_c, wind_kmh, precip, category))
    assert out.loc[0, "outdoor_work_risk"] == expected


def test_deduplicate_keeps_the_latest_ingested_row():
    t = pd.Timestamp("2026-11-10 00:00", tz="UTC")
    df = pd.DataFrame({
        "city": ["London", "London"],
        "observed_at_utc": [t, t],
        "temperature_c": [2.0, 1.0],
        "ingested_at_utc": ["2026-11-10T02:00:00+00:00", "2026-11-10T01:00:00+00:00"],
    })
    out = deduplicate(df)
    assert len(out) == 1
    assert out.loc[0, "temperature_c"] == 2.0


def test_transform_returns_all_expected_columns(london_payload, wmo):
    out = transform([("London", london_payload)], wmo, ingested_at=INGESTED)
    assert list(out.columns) == COLUMNS
    assert len(out) == 6


def test_transform_removes_duplicate_hours(london_payload, wmo):
    out = transform([("London", london_payload), ("London", london_payload)], wmo, ingested_at=INGESTED)
    assert len(out) == 6


def test_transform_rejects_empty_input(wmo):
    with pytest.raises(ValueError):
        transform([], wmo)