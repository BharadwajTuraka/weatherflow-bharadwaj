"""Load: Parquet output and an idempotent star-schema load into SQLite."""
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

FACT_COLUMNS = [
    "city_id", "date_id", "observed_at_utc", "hour_local",
    "temperature_c", "temperature_f", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "wind_speed_ms", "beaufort_scale",
    "weather_code", "weather_description", "weather_category",
    "is_daylight", "outdoor_work_risk", "source", "ingested_at_utc",
]
KEY_COLUMNS = ["city_id", "observed_at_utc", "source"]
UPDATE_COLUMNS = [c for c in FACT_COLUMNS if c not in KEY_COLUMNS]

UPSERT_SQL = (
    f"INSERT INTO fact_weather_hourly ({', '.join(FACT_COLUMNS)}) "
    f"VALUES ({', '.join('?' * len(FACT_COLUMNS))}) "
    f"ON CONFLICT ({', '.join(KEY_COLUMNS)}) DO UPDATE SET "
    + ", ".join(f"{c} = excluded.{c}" for c in UPDATE_COLUMNS)
)


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database with foreign keys switched on."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """Create all tables from sql/schema.sql if they do not exist yet."""
    conn.executescript(Path(schema_path).read_text(encoding="utf-8"))


def build_dim_date(start: str, end: str) -> list[tuple]:
    """Build one dim_date row per day between start and end (inclusive)."""
    days = pd.date_range(start, end, freq="D")
    return [
        (int(d.strftime("%Y%m%d")), d.strftime("%Y-%m-%d"), d.day_name(),
        int(d.day_of_week >= 5), d.month, d.year)
        for d in days
    ]


def upsert_cities(conn: sqlite3.Connection, cities: list[dict]) -> dict:
    """Upsert dim_city from config and return a {city_name: city_id} map."""
    conn.executemany(
        "INSERT INTO dim_city (city_name, country, latitude, longitude) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (city_name) DO UPDATE SET country = excluded.country, "
        "latitude = excluded.latitude, longitude = excluded.longitude",
        [(c["name"], c.get("country", "United Kingdom"), c["latitude"], c["longitude"])
         for c in cities],
    )
    return dict(conn.execute("SELECT city_name, city_id FROM dim_city").fetchall())
def get_watermarks(conn: sqlite3.Connection, source: str, now_utc: datetime) -> dict:
    """Return {city_name: latest loaded hour that has already happened (UTC)} for one source.

    Hours in the future (forecast rows) are ignored, otherwise the mark would sit up to a
    day ahead and the next run would skip every hour in between.
    """
    rows = conn.execute(
        "SELECT c.city_name, MAX(f.observed_at_utc) FROM fact_weather_hourly f "
        "JOIN dim_city c ON c.city_id = f.city_id "
        "WHERE f.source = ? AND f.observed_at_utc <= ? GROUP BY c.city_name",
        (source, now_utc.strftime("%Y-%m-%dT%H:%M")),
    ).fetchall()
    return {name: pd.Timestamp(latest, tz="UTC") for name, latest in rows if latest}

def to_fact_rows(df: pd.DataFrame, city_ids: dict, source: str) -> list[tuple]:
    """Turn the transformed table into rows matching FACT_COLUMNS."""
    out = df.copy()
    out["city_id"] = out["city"].map(city_ids)
    if out["city_id"].isna().any():
        raise ValueError("Some cities are missing from dim_city")
    out["city_id"] = out["city_id"].astype(int)
    out["date_id"] = out["observed_at_local"].dt.strftime("%Y%m%d").astype(int)
    out["hour_local"] = out["observed_at_local"].dt.hour
    out["observed_at_utc"] = out["observed_at_utc"].dt.strftime("%Y-%m-%dT%H:%M")
    out["is_daylight"] = out["is_daylight"].astype(int)
    out["source"] = source
    cols = out[FACT_COLUMNS].astype(object)
    cols = cols.where(cols.notna(), None)
    return list(cols.itertuples(index=False, name=None))


def load(df: pd.DataFrame, config: dict, source: str = "open_meteo_forecast") -> int:
    """Upsert dimensions and facts in ONE transaction. Safe to re-run."""
    paths = config["paths"]
    conn = connect(paths["database"])
    try:
        apply_schema(conn, paths["schema_sql"])
        with conn:  # commits on success, rolls back on any error
            conn.executemany(
                "INSERT OR IGNORE INTO dim_date VALUES (?, ?, ?, ?, ?, ?)",
                build_dim_date(config["dim_date"]["start"], config["dim_date"]["end"]),
            )
            city_ids = upsert_cities(conn, config["cities"])
            rows = to_fact_rows(df, city_ids, source)
            conn.executemany(UPSERT_SQL, rows)
    finally:
        conn.close()
    logger.info("Loaded %d rows into fact_weather_hourly (%s)", len(rows), paths["database"])
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