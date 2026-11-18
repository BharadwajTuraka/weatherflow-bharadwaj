"""Transform: flatten, rename, clean and de-duplicate."""
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

RENAME = {
    "time": "observed_at_utc",
    "temperature_2m": "temperature_c",
    "apparent_temperature": "feels_like_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}
COLUMNS = [
    "city", "observed_at_utc", "temperature_c", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "weather_code", "ingested_at_utc",
]


def flatten_payload(payload: dict, city: str) -> pd.DataFrame:
    """Turn one city's nested JSON into a table with one row per hour."""
    df = pd.DataFrame(payload["hourly"])
    df["city"] = city
    return df


def transform(raw: list[tuple[str, dict]]) -> pd.DataFrame:
    """Combine all cities, rename columns, convert time, add metadata, de-duplicate."""
    if not raw:
        raise ValueError("No raw data to transform")
    df = pd.concat([flatten_payload(p, c) for c, p in raw], ignore_index=True)
    df = df.rename(columns=RENAME)
    df["observed_at_utc"] = pd.to_datetime(df["observed_at_utc"])
    df["ingested_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df = df.drop_duplicates(subset=["city", "observed_at_utc"], keep="last")
    logger.info("Transformed %d rows", len(df))
    return df[COLUMNS]