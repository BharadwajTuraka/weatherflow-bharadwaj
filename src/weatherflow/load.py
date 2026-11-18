"""Load: write rows into SQLite. Re-running replaces rows instead of duplicating."""
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from weatherflow.transform import COLUMNS

logger = logging.getLogger(__name__)

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
    df = df.copy()
    df["observed_at_utc"] = df["observed_at_utc"].dt.strftime("%Y-%m-%dT%H:%M")
    df = df.astype(object).where(df.notna(), None)
    rows = list(df.itertuples(index=False, name=None))
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_SQL)
        conn.executemany(
            f"INSERT OR REPLACE INTO weather_hourly ({','.join(COLUMNS)}) "
            f"VALUES ({','.join('?' * len(COLUMNS))})",
            rows,
        )
    logger.info("Loaded %d rows into %s", len(rows), db_path)
    return len(rows)