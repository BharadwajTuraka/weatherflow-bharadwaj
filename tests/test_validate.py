"""Unit tests for the data quality checks."""
from datetime import datetime, timezone

import pandas as pd
import pytest

from weatherflow.validate import DataQualityError, validate, write_dq_report, write_quarantine

CITIES = ["London"]


def get_result(results, name):
    """Find one check result by name."""
    return next(r for r in results if r.name == name)


def test_clean_data_passes_every_blocking_and_quarantine_check(clean_df, dq_cfg):
    good, bad, results = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert len(good) == 6
    assert bad.empty
    assert all(r.passed for r in results if r.severity in ("quarantine", "fail"))


def test_99_degree_reading_is_quarantined_with_reason(clean_df, dq_cfg):
    clean_df.loc[0, "temperature_c"] = 99.0
    good, bad, _ = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert len(good) == 5
    assert len(bad) == 1
    assert bad.iloc[0]["dq_failure_reason"] == "temperature_out_of_range"


def test_negative_precipitation_is_quarantined(clean_df, dq_cfg):
    clean_df.loc[1, "precipitation_mm"] = -1.0
    _, bad, _ = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert bad.iloc[0]["dq_failure_reason"] == "negative_precipitation_or_wind"


def test_humidity_above_100_is_quarantined(clean_df, dq_cfg):
    clean_df.loc[2, "humidity_pct"] = 150
    _, bad, _ = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert bad.iloc[0]["dq_failure_reason"] == "humidity_out_of_range"


def test_missing_temperature_is_quarantined(clean_df, dq_cfg):
    clean_df.loc[3, "temperature_c"] = float("nan")
    _, bad, _ = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert bad.iloc[0]["dq_failure_reason"] == "missing_required_field"


def test_a_row_with_two_problems_records_both_reasons(clean_df, dq_cfg):
    clean_df.loc[0, "temperature_c"] = 99.0
    clean_df.loc[0, "wind_speed_kmh"] = -5.0
    _, bad, _ = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert bad.iloc[0]["dq_failure_reason"] == "temperature_out_of_range;negative_precipitation_or_wind"


def test_duplicate_row_fails_the_run(clean_df, dq_cfg):
    duplicated = pd.concat([clean_df, clean_df.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataQualityError) as excinfo:
        validate(duplicated, dq_cfg, CITIES, check_timeliness=False)
    assert "unique_keys" in str(excinfo.value)


def test_city_with_too_few_hours_fails_the_run(clean_df, dq_cfg):
    with pytest.raises(DataQualityError) as excinfo:
        validate(clean_df.iloc[:3], dq_cfg, CITIES, check_timeliness=False)
    assert "expected_hours_per_city" in str(excinfo.value)


def test_missing_city_fails_the_run(clean_df, dq_cfg):
    with pytest.raises(DataQualityError) as excinfo:
        validate(clean_df, dq_cfg, ["London", "Cardiff"], check_timeliness=False)
    assert "expected_hours_per_city" in str(excinfo.value)


def test_fresh_data_passes_the_timeliness_check(clean_df, dq_cfg):
    now = datetime(2026, 11, 10, 6, 30, tzinfo=timezone.utc)
    _, _, results = validate(clean_df, dq_cfg, CITIES, now=now)
    assert get_result(results, "data_freshness").passed


def test_stale_data_gives_a_timeliness_warning_but_does_not_fail(clean_df, dq_cfg):
    now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    good, _, results = validate(clean_df, dq_cfg, CITIES, now=now)
    freshness = get_result(results, "data_freshness")
    assert not freshness.passed
    assert freshness.severity == "warn"
    assert len(good) == 6


def test_forecast_rows_in_the_future_are_ignored_by_the_timeliness_check(clean_df, dq_cfg):
    future = clean_df.iloc[[0]].copy()
    future["observed_at_utc"] = future["observed_at_utc"] + pd.Timedelta(days=1)
    df = pd.concat([clean_df, future], ignore_index=True)
    now = datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
    _, _, results = validate(df, dq_cfg, CITIES, now=now)
    assert not get_result(results, "data_freshness").passed


def test_large_feels_like_gap_warns_but_keeps_the_row(clean_df, dq_cfg):
    clean_df.loc[0, "feels_like_c"] = -20.0
    good, bad, results = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    check = get_result(results, "feels_like_consistency")
    assert not check.passed
    assert check.failed_rows == 1
    assert len(good) == 6
    assert bad.empty


def test_unknown_weather_code_gives_a_warning(clean_df, dq_cfg):
    clean_df.loc[0, "weather_description"] = "unknown"
    _, _, results = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    assert get_result(results, "known_weather_code").failed_rows == 1


def test_write_quarantine_returns_none_when_there_are_no_bad_rows(tmp_path):
    assert write_quarantine(pd.DataFrame(), tmp_path) is None


def test_write_quarantine_saves_rows_with_the_failure_reason(tmp_path, clean_df):
    bad = clean_df.iloc[:1].copy()
    bad["dq_failure_reason"] = "temperature_out_of_range"
    path = write_quarantine(bad, tmp_path)
    assert path.exists()
    assert "dq_failure_reason" in pd.read_parquet(path).columns


def test_dq_report_lists_every_check(tmp_path, clean_df, dq_cfg):
    _, _, results = validate(clean_df, dq_cfg, CITIES, check_timeliness=False)
    path = write_dq_report(results, tmp_path, rows_in=6, rows_good=6, rows_quarantined=0)
    text = path.read_text(encoding="utf-8")
    assert "unique_keys" in text
    assert "Rows in: 6" in text