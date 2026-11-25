"""Tests for the cross-source temperature check."""
import sqlite3

from weatherflow.crosscheck import cross_source_report


def make_db(tmp_path, rows):
    """Create a tiny database with just the columns the check reads."""
    db = tmp_path / "x.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE dim_city (city_id INTEGER PRIMARY KEY, city_name TEXT)")
    conn.execute(
        "CREATE TABLE fact_weather_hourly (city_id INTEGER, observed_at_utc TEXT, "
        "source TEXT, temperature_c REAL)"
    )
    conn.execute("INSERT INTO dim_city VALUES (1, 'London')")
    conn.executemany("INSERT INTO fact_weather_hourly VALUES (1, ?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return db


def test_sources_that_agree_give_no_disagreements(tmp_path):
    rows = [("2026-11-25T00:00", "open_meteo_forecast", 5.0), ("2026-11-25T00:00", "weatherapi_forecast", 5.5)]
    report = cross_source_report(make_db(tmp_path, rows), 3.0)
    assert report["compared"] == 1
    assert report["disagreements"] == 0


def test_a_large_gap_is_counted_as_a_disagreement(tmp_path):
    rows = [("2026-11-25T00:00", "open_meteo_forecast", 5.0), ("2026-11-25T00:00", "weatherapi_forecast", 9.0)]
    report = cross_source_report(make_db(tmp_path, rows), 3.0)
    assert report["disagreements"] == 1
    assert report["worst_city"] == "London"


def test_a_single_source_compares_nothing(tmp_path):
    rows = [("2026-11-25T00:00", "open_meteo_forecast", 5.0)]
    report = cross_source_report(make_db(tmp_path, rows), 3.0)
    assert report["compared"] == 0