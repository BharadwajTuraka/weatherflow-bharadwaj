"""Tests for the pipeline wiring, with extract mocked."""
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
        "cities": [{"name": "London", "country": "United Kingdom", "latitude": 51.5, "longitude": -0.12}],
    }


def test_run_loads_rows_and_writes_a_dq_report(monkeypatch, pipeline_config, london_payload):
    monkeypatch.setattr(pipeline, "extract", lambda config: [("London", london_payload)])
    assert pipeline.run(pipeline_config) == 6
    assert len(list(pipeline_config["paths"]["dq_report_dir"].glob("*.md"))) == 1


def test_run_returns_zero_when_nothing_was_extracted(monkeypatch, pipeline_config):
    monkeypatch.setattr(pipeline, "extract", lambda config: [])
    assert pipeline.run(pipeline_config) == 0


def test_a_blocking_check_stops_the_load_but_still_writes_a_report(monkeypatch, pipeline_config, london_payload):
    monkeypatch.setattr(pipeline, "extract", lambda config: [("London", london_payload)])
    pipeline_config["dq"] = {**pipeline_config["dq"], "min_hours_per_city": 100}
    with pytest.raises(DataQualityError):
        pipeline.run(pipeline_config)
    assert not pipeline_config["paths"]["database"].exists()
    assert len(list(pipeline_config["paths"]["dq_report_dir"].glob("*.md"))) == 1