"""Validate: data quality checks, quarantine and a DQ report."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Raised when a blocking data quality check fails. Carries the results so far."""

    def __init__(self, message: str, results: list, quarantined: pd.DataFrame):
        super().__init__(message)
        self.results = results
        self.quarantined = quarantined


@dataclass
class CheckResult:
    """Outcome of one data quality check."""

    name: str
    dimension: str
    severity: str  # "quarantine" | "fail" | "warn"
    passed: bool
    failed_rows: int
    details: str


def _result(name: str, dimension: str, severity: str, bad_mask: pd.Series, details: str) -> CheckResult:
    """Build a CheckResult from a boolean mask of failing rows."""
    failed = int(bad_mask.sum())
    return CheckResult(name, dimension, severity, failed == 0, failed, details)


def validate(
    df: pd.DataFrame,
    dq_cfg: dict,
    expected_cities: list[str],
    now: datetime | None = None,
    check_timeliness: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, list[CheckResult]]:
    """Run all checks. Return (good_rows, quarantined_rows, results).

    Raises DataQualityError if any blocking ('fail') check fails.
    """
    now = now or datetime.now(timezone.utc)
    results: list[CheckResult] = []

    # Row-level checks that quarantine bad rows
    required = ["city", "observed_at_utc", "temperature_c"]
    flags = {
        "missing_required_field": df[required].isna().any(axis=1),
        "temperature_out_of_range": (df["temperature_c"] < dq_cfg["temperature_min_c"])
        | (df["temperature_c"] > dq_cfg["temperature_max_c"]),
        "humidity_out_of_range": (df["humidity_pct"] < dq_cfg["humidity_min_pct"])
        | (df["humidity_pct"] > dq_cfg["humidity_max_pct"]),
        "negative_precipitation_or_wind": (df["precipitation_mm"] < 0) | (df["wind_speed_kmh"] < 0),
    }
    details = {
        "missing_required_field": "city, observed_at_utc and temperature_c must not be null",
        "temperature_out_of_range": f"temperature_c between {dq_cfg['temperature_min_c']} and {dq_cfg['temperature_max_c']}",
        "humidity_out_of_range": f"humidity_pct between {dq_cfg['humidity_min_pct']} and {dq_cfg['humidity_max_pct']}",
        "negative_precipitation_or_wind": "precipitation_mm and wind_speed_kmh must be >= 0",
    }
    dimensions = {
        "missing_required_field": "completeness",
        "temperature_out_of_range": "validity",
        "humidity_out_of_range": "validity",
        "negative_precipitation_or_wind": "validity",
    }
    for name, mask in flags.items():
        results.append(_result(name, dimensions[name], "quarantine", mask, details[name]))

    bad = pd.DataFrame(flags)
    quarantine_mask = bad.any(axis=1)
    columns = list(bad.columns)
    reason_text = pd.Series(
        [";".join(c for c, hit in zip(columns, row) if hit) for row in bad.to_numpy()],
        index=df.index,
    )
    quarantined = df[quarantine_mask].copy()
    quarantined["dq_failure_reason"] = reason_text[quarantine_mask]
    good = df[~quarantine_mask].copy()

    # Row-level warnings (rows are kept)
    gap = (df["feels_like_c"] - df["temperature_c"]).abs() > dq_cfg["max_feels_like_gap_c"]
    results.append(_result(
        "feels_like_consistency", "consistency", "warn", gap,
        f"feels_like_c within {dq_cfg['max_feels_like_gap_c']} C of temperature_c",
    ))
    unknown_code = df["weather_description"] == "unknown"
    results.append(_result(
        "known_weather_code", "validity", "warn", unknown_code,
        "weather_code must exist in the WMO reference table",
    ))

    # Dataset-level checks
    key = ["city", "observed_at_utc"] + (["source"] if "source" in df.columns else [])
    results.append(_result(
        "unique_keys", "uniqueness", "fail", df.duplicated(key, keep=False),
        f"no duplicate {tuple(key)}",
    ))

    counts = good.groupby("city").size().reindex(expected_cities, fill_value=0)
    short = counts[counts < dq_cfg["min_hours_per_city"]]
    results.append(CheckResult(
        "expected_hours_per_city", "completeness", "fail", short.empty, int(len(short)),
        "every city has at least %d hours" % dq_cfg["min_hours_per_city"]
        + ("" if short.empty else "; short: " + ", ".join(f"{c}={n}" for c, n in short.items())),
    ))

    if check_timeliness:
        ts_now = pd.Timestamp(now)
        past = good[good["observed_at_utc"] <= ts_now]
        if past.empty:
            results.append(CheckResult(
                "data_freshness", "timeliness", "warn", False, 0, "no observations in the past",
            ))
        else:
            age_h = (ts_now - past["observed_at_utc"].max()).total_seconds() / 3600
            results.append(CheckResult(
                "data_freshness", "timeliness", "warn", age_h <= dq_cfg["max_data_age_hours"], 0,
                f"latest past observation is {age_h:.1f} h old (limit {dq_cfg['max_data_age_hours']} h)",
            ))

    blocking = [r.name for r in results if r.severity == "fail" and not r.passed]
    if blocking:
        raise DataQualityError("blocking checks failed: " + ", ".join(blocking), results, quarantined)
    return good, quarantined, results


def write_quarantine(quarantined: pd.DataFrame, quarantine_dir: Path) -> Path | None:
    """Write quarantined rows to quarantine_dir/run_date=<date>/ (nothing if there are none)."""
    if quarantined.empty:
        return None
    now = datetime.now(timezone.utc)
    folder = Path(quarantine_dir) / f"run_date={now:%Y-%m-%d}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"quarantine-{now:%Y%m%dT%H%M%S}.parquet"
    quarantined.to_parquet(path, index=False)
    logger.warning("Quarantined %d rows to %s", len(quarantined), path)
    return path


def write_dq_report(
    results: list[CheckResult], report_dir: Path, rows_in: int, rows_good: int, rows_quarantined: int
) -> Path:
    """Write a Markdown summary of one run's checks to report_dir/<timestamp>.md."""
    now = datetime.now(timezone.utc)
    folder = Path(report_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now:%Y%m%dT%H%M%S}.md"
    lines = [
        f"# Data quality report {now:%Y-%m-%d %H:%M:%S} UTC",
        "",
        f"- Rows in: {rows_in}",
        f"- Rows passed: {rows_good}",
        f"- Rows quarantined: {rows_quarantined}",
        "",
        "| Check | Dimension | Severity | Result | Failed | Details |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        outcome = "PASS" if r.passed else "FAIL"
        lines.append(f"| {r.name} | {r.dimension} | {r.severity} | {outcome} | {r.failed_rows} | {r.details} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("DQ report written to %s", path)
    return path