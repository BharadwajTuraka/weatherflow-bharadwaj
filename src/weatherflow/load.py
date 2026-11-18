"""Load: write rows into SQLite and Parquet."""
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

LOAD_COLUMNS = [
    "city", "observed_at_utc", "temperature_c", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "weather_code", "ingested_at_utc",
]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS weather_hourly (
    city              TEXT    NOT NULL,
    observed_at_utc   TEXT    NOT NULL,
    temperature_c     REAL,
    feels_like_c      REAL,
    humidity_pct      INTEGER,
    precipitation_mm  REAL,
    wind_speed_kmh    REAL,
    weather_code      INTEGER,
    ingested_at_utc   TEXT    NOT NULL,
    PRIMARY KEY (city, observed_at_utc)
);
"""


def load(df: pd.DataFrame, db_path: Path) -> int:
    """Upsert the DataFrame into weather_hourly and return the number of rows written."""
    out = df[LOAD_COLUMNS].copy()
    out["observed_at_utc"] = out["observed_at_utc"].dt.strftime("%Y-%m-%dT%H:%M")
    out = out.astype(object).where(out.notna(), None)
    rows = list(out.itertuples(index=False, name=None))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_SQL)
        conn.executemany(
            f"INSERT OR REPLACE INTO weather_hourly ({','.join(LOAD_COLUMNS)}) "
            f"VALUES ({','.join('?' * len(LOAD_COLUMNS))})",
            rows,
        )
    logger.info("Loaded %d rows into %s", len(rows), db_path)
    return len(rows)


def write_parquet(df: pd.DataFrame, processed_dir: Path) -> Path:
    """Write the table to processed_dir/weather_hourly/run_date=<date>/part-<timestamp>.parquet."""
    now = datetime.now(timezone.utc)
    folder = Path(processed_dir) / "weather_hourly" / f"run_date={now:%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"part-{now:%Y%m%dT%H%M%S}.parquet"
    df.to_parquet(path, index=False)
    logger.info("Wrote %d rows to %s", len(df), path)
    return path