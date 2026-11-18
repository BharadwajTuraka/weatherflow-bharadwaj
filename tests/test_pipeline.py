"""Tests for the pipeline wiring, with extract mocked."""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from weatherflow import pipeline
from weatherflow.validate import DataQualityError

SCHEMA = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"


@pytest.fixture
def pipeline_config(tmp_path, dq_cfg, wmo):
    """A full config pointing at temporary folders."""
    wmo_path = tmp_path / "wmo.csv"
    wmo.to_csv(wmo_path, index=False)
    london = {"name": "London", "country": "United Kingdom", "latitude": 51.5, "longitude": -0.12}
    return {
        "paths": {
            "wmo_codes": wmo_path,
            "processed_dir": tmp_path / "processed",
            "quarantine_dir": tmp_path / "quarantine",
            "dq_report_dir": tmp_path / "reports",
            "database": tmp_path / "weather.db",
            "schema_sql": SCHEMA,
        },
        "dq": dq_cfg,
        "dim_date": {"start": "2025-01-01", "end": "2027-12-31"},
        "incremental": {"overlap_hours": 2},
        "backfill": {"chunk_days": 7, "lag_days": 5, "sleep_seconds": 0},
        "cities": [london],
    }


def test_run_loads_rows_and_writes_a_dq_report(monkeypatch, pipeline_config, london_payload):
    monkeypatch.setattr(pipeline, "extract", lambda config, starts=None: [("London", london_payload)])
    assert pipeline.run(pipeline_config) == 6
    assert len(list(pipeline_config["paths"]["dq_report_dir"].glob("*.md"))) == 1


def test_run_returns_zero_when_nothing_was_extracted(monkeypatch, pipeline_config):
    monkeypatch.setattr(pipeline, "extract", lambda config, starts=None: [])
    assert pipeline.run(pipeline_config) == 0


def test_a_blocking_check_stops_the_load_but_still_writes_a_report(monkeypatch, pipeline_config, london_payload):
    monkeypatch.setattr(pipeline, "extract", lambda config, starts=None: [("London", london_payload)])
    pipeline_config["dq"] = {**pipeline_config["dq"], "min_hours_per_city": 100}
    with pytest.raises(DataQualityError):
        pipeline.run(pipeline_config)
    assert not pipeline_config["paths"]["database"].exists()
    assert len(list(pipeline_config["paths"]["dq_report_dir"].glob("*.md"))) == 1


def test_first_run_has_no_watermark_so_it_requests_the_default_window(pipeline_config):
    assert pipeline.incremental_starts(pipeline_config) == {}


def test_second_run_starts_at_watermark_minus_overlap(monkeypatch, pipeline_config, london_payload):
    monkeypatch.setattr(pipeline, "extract", lambda config, starts=None: [("London", london_payload)])
    pipeline.run(pipeline_config)
    last = datetime.fromisoformat(london_payload["hourly"]["time"][-1]).replace(tzinfo=timezone.utc)
    now = last + timedelta(hours=7)
    starts = pipeline.incremental_starts(pipeline_config, now=now)
    assert starts == {"London": (last - timedelta(hours=2)).date()}



def test_incremental_passes_each_cities_start_date_to_extract(monkeypatch, pipeline_config, london_payload):
    seen = {}

    def fake_extract(config, starts=None):
        seen["starts"] = starts
        return [("London", london_payload)]

    monkeypatch.setattr(pipeline, "extract", fake_extract)
    pipeline.run(pipeline_config)
    assert seen["starts"] == {}  # empty database: default window
    pipeline.run(pipeline_config)
    assert "London" in seen["starts"]  # second run uses the watermark


def test_backfill_uses_the_archive_source_and_the_same_load_path(monkeypatch, pipeline_config, london_payload):
    monkeypatch.setattr(pipeline, "extract_archive", lambda config, start, end: [("London", london_payload)])
    assert pipeline.backfill(pipeline_config, days=30) == 6
    conn = sqlite3.connect(pipeline_config["paths"]["database"])
    try:
        sources = conn.execute("SELECT DISTINCT source FROM fact_weather_hourly").fetchall()
    finally:
        conn.close()
    assert sources == [("open_meteo_archive",)]


def test_backfill_ends_at_today_minus_the_lag_by_default(monkeypatch, pipeline_config, london_payload):
    seen = {}

    def fake_archive(config, start, end):
        seen["start"], seen["end"] = start, end
        return [("London", london_payload)]

    monkeypatch.setattr(pipeline, "extract_archive", fake_archive)
    pipeline.backfill(pipeline_config, days=30)
    today = datetime.now(timezone.utc).date()
    assert seen["end"] == today - timedelta(days=5)
    assert (seen["end"] - seen["start"]).days == 29