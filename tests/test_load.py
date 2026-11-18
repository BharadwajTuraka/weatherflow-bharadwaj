"""Integration tests for the star-schema load."""
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from weatherflow.load import FACT_COLUMNS, apply_schema, build_dim_date, connect, load, to_fact_rows, write_parquet
from weatherflow.transform import transform

SCHEMA = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"


@pytest.fixture
def config(tmp_path):
    """A config that points at a temporary database."""
    return {
        "paths": {"database": tmp_path / "test.db", "schema_sql": SCHEMA},
        "dim_date": {"start": "2025-01-01", "end": "2027-12-31"},
        "cities": [{"name": "London", "country": "United Kingdom", "latitude": 51.5, "longitude": -0.12}],
    }


@pytest.fixture
def transformed(london_payload, wmo):
    """The London fixture after the transform step."""
    return transform([("London", london_payload)], wmo, ingested_at="2026-11-18T09:00:00+00:00")


def count_rows(db_path, table="fact_weather_hourly"):
    """Count rows in a table, closing the connection afterwards."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_loading_the_same_data_three_times_does_not_change_the_row_count(config, transformed):
    db = config["paths"]["database"]
    for _ in range(3):
        assert load(transformed, config) == 6
        assert count_rows(db) == 6


def test_reloading_updates_changed_values_instead_of_duplicating(config, transformed):
    db = config["paths"]["database"]
    load(transformed, config)
    changed = transformed.copy()
    changed.loc[0, "temperature_c"] = 42.0
    load(changed, config)
    conn = sqlite3.connect(db)
    try:
        value = conn.execute(
            "SELECT temperature_c FROM fact_weather_hourly ORDER BY observed_at_utc LIMIT 1"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count_rows(db) == 6
    assert value == 42.0


def test_a_failed_load_leaves_no_partial_rows(config, transformed):
    bad = transformed.copy()
    bad.loc[3, "outdoor_work_risk"] = "extreme"  # violates the CHECK constraint
    with pytest.raises(sqlite3.IntegrityError):
        load(bad, config)
    assert count_rows(config["paths"]["database"]) == 0


def test_schema_creates_the_three_star_tables(config):
    conn = connect(config["paths"]["database"])
    try:
        apply_schema(conn, SCHEMA)
        names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        conn.close()
    assert {"dim_city", "dim_date", "fact_weather_hourly"} <= names


def test_dim_date_has_one_row_per_day_and_flags_weekends():
    rows = build_dim_date("2026-11-14", "2026-11-16")  # Saturday to Monday
    assert [r[0] for r in rows] == [20261114, 20261115, 20261116]
    assert rows[0][2] == "Saturday"
    assert [r[3] for r in rows] == [1, 1, 0]


def test_fact_date_is_the_london_local_date(transformed):
    df = transformed.iloc[:1].copy()
    df["observed_at_utc"] = pd.to_datetime(["2026-06-30 23:30"], utc=True)
    df["observed_at_local"] = df["observed_at_utc"].dt.tz_convert("Europe/London")
    row = to_fact_rows(df, {"London": 1}, "open_meteo_forecast")[0]
    assert row[FACT_COLUMNS.index("date_id")] == 20260701
    assert row[FACT_COLUMNS.index("hour_local")] == 0


def test_a_city_missing_from_dim_city_is_rejected(transformed):
    with pytest.raises(ValueError):
        to_fact_rows(transformed, {}, "open_meteo_forecast")


def test_write_parquet_creates_a_partitioned_file(tmp_path, transformed):
    path = write_parquet(transformed, tmp_path)
    assert path.suffix == ".parquet"
    assert path.parent.name.startswith("run_date=")
    assert len(pd.read_parquet(path)) == 6