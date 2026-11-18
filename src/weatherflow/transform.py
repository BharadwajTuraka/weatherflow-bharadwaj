"""Transform: small pure functions that turn raw API JSON into a clean table."""
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

RENAME = {
    "time": "observed_at_utc",
    "temperature_2m": "temperature_c",
    "apparent_temperature": "feels_like_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
    "is_day": "is_daylight",
}

# Beaufort scale 0-12, lower bound of each force in m/s (right edge excluded)
BEAUFORT_BINS = [-np.inf, 0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7, np.inf]

COLUMNS = [
    "city", "observed_at_utc", "observed_at_local",
    "temperature_c", "temperature_f", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "wind_speed_ms", "beaufort_scale",
    "weather_code", "weather_description", "weather_category",
    "is_daylight", "outdoor_work_risk", "ingested_at_utc",
]


def flatten_payload(payload: dict, city: str) -> pd.DataFrame:
    """Turn one city's nested JSON into a table with one row per hour."""
    df = pd.DataFrame(payload["hourly"])
    df["city"] = city
    return df


def standardise_columns(df: pd.DataFrame, ingested_at: str | None = None) -> pd.DataFrame:
    """Rename columns, parse UTC time, derive London time and add ingestion metadata."""
    out = df.rename(columns=RENAME)
    out["observed_at_utc"] = pd.to_datetime(out["observed_at_utc"], utc=True)
    out["observed_at_local"] = out["observed_at_utc"].dt.tz_convert("Europe/London")
    out["is_daylight"] = out["is_daylight"].astype(bool)
    out["ingested_at_utc"] = ingested_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return out


def add_weather_description(df: pd.DataFrame, wmo: pd.DataFrame) -> pd.DataFrame:
    """Join WMO code descriptions and categories. Unknown codes become 'unknown'."""
    lookup = wmo[["code", "description", "category"]].rename(
        columns={
            "code": "weather_code",
            "description": "weather_description",
            "category": "weather_category",
        }
    )
    out = df.merge(lookup, on="weather_code", how="left")
    out["weather_description"] = out["weather_description"].fillna("unknown")
    out["weather_category"] = out["weather_category"].fillna("unknown")
    return out


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add Fahrenheit, wind in m/s, Beaufort scale and outdoor_work_risk."""
    out = df.copy()
    out["temperature_f"] = out["temperature_c"] * 9 / 5 + 32
    out["wind_speed_ms"] = out["wind_speed_kmh"] / 3.6
    out["beaufort_scale"] = pd.cut(
        out["wind_speed_ms"], bins=BEAUFORT_BINS, labels=False, right=False
    ).astype("Int64")

    beaufort = out["beaufort_scale"].fillna(0).astype(int)
    high = (
        (beaufort >= 7)
        | out["weather_category"].isin(["storm", "snow"])
        | (out["precipitation_mm"] >= 4)
    )
    medium = (
        (beaufort >= 5)
        | (out["precipitation_mm"] >= 1)
        | (out["temperature_c"] <= 0)
    )
    out["outdoor_work_risk"] = np.select([high, medium], ["high", "medium"], default="low")
    return out


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the latest ingested row for each (city, observed_at_utc)."""
    return (
        df.sort_values("ingested_at_utc", kind="stable")
        .drop_duplicates(subset=["city", "observed_at_utc"], keep="last")
        .sort_values(["city", "observed_at_utc"])
        .reset_index(drop=True)
    )


def transform(
    raw: list[tuple[str, dict]], wmo: pd.DataFrame, ingested_at: str | None = None
) -> pd.DataFrame:
    """Run every transformation step in order and return the final table."""
    if not raw:
        raise ValueError("No raw data to transform")
    df = pd.concat([flatten_payload(p, c) for c, p in raw], ignore_index=True)
    df = standardise_columns(df, ingested_at)
    df = deduplicate(df)
    df = add_weather_description(df, wmo)
    df = add_derived_metrics(df)
    logger.info("Transformed %d rows", len(df))
    return df[COLUMNS]