import sqlite3
from datetime import datetime, timezone
import pandas as pd
from extract import extract

RENAME = {
    "time": "observed_at",
    "temperature_2m": "temperature_c",
    "apparent_temperature": "feels_like_c",
    "relative_humidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}
COLUMNS = ["city", "observed_at", "temperature_c", "feels_like_c", "humidity_pct",
           "precipitation_mm", "wind_speed_kmh", "weather_code", "ingested_at_utc"]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS weather_hourly (
    city              TEXT    NOT NULL,
    observed_at       TEXT    NOT NULL,
    temperature_c     REAL,
    feels_like_c      REAL,
    humidity_pct      INTEGER,
    precipitation_mm  REAL,
    wind_speed_kmh    REAL,
    weather_code      INTEGER,
    ingested_at_utc   TEXT    NOT NULL,
    PRIMARY KEY (city, observed_at)
);
"""

def flatten(payload: dict, city_name: str) -> pd.DataFrame:
    df = pd.DataFrame(payload["hourly"])
    df["city"] = city_name
    return df

def transform(raw: list[tuple[str, dict]]) -> pd.DataFrame:
    df = pd.concat([flatten(p, c) for c, p in raw], ignore_index=True)
    df = df.rename(columns=RENAME)
    df["observed_at"] = pd.to_datetime(df["observed_at"])
    df["ingested_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df = df.drop_duplicates(subset=["city", "observed_at"], keep="last")
    return df[COLUMNS]

def load(df: pd.DataFrame, db_path: str = "weather.db") -> int:
    df = df.copy()
    df["observed_at"] = df["observed_at"].dt.strftime("%Y-%m-%dT%H:%M")
    df = df.astype(object).where(df.notna(), None)
    rows = list(df.itertuples(index=False, name=None))
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_SQL)
        conn.executemany(
            f"INSERT OR REPLACE INTO weather_hourly ({','.join(COLUMNS)}) "
            f"VALUES ({','.join('?' * len(COLUMNS))})", rows)
    return len(rows)

def main():
    raw = extract()
    df = transform(raw)
    rows = load(df)
    print(f"Loaded {rows} rows")

if __name__ == "__main__":
    main()