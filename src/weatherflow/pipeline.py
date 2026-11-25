"""Wire extract, transform, validate and load together."""
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from weatherflow.extract import extract, extract_archive, extract_weatherapi
from weatherflow.load import connect, get_watermarks, load, write_parquet
from weatherflow.normalise import normalise_weatherapi
from weatherflow.transform import transform, transform_canonical
from weatherflow.validate import DataQualityError, validate, write_dq_report, write_quarantine

logger = logging.getLogger(__name__)

FORECAST_SOURCE = "open_meteo_forecast"
ARCHIVE_SOURCE = "open_meteo_archive"
WEATHERAPI_SOURCE = "weatherapi_forecast"


def process_frame(
    df: pd.DataFrame, config: dict, source: str, check_timeliness: bool, min_hours: int | None = None
) -> int:
    """Validate and load an already transformed table. Shared by every source."""
    paths = config["paths"]
    dq_cfg = dict(config["dq"])
    if min_hours is not None:
        dq_cfg["min_hours_per_city"] = min_hours
    cities = [c["name"] for c in config["cities"]]
    try:
        good, quarantined, results = validate(df, dq_cfg, cities, check_timeliness=check_timeliness)
    except DataQualityError as exc:
        write_quarantine(exc.quarantined, paths["quarantine_dir"])
        write_dq_report(
            exc.results, paths["dq_report_dir"], len(df),
            len(df) - len(exc.quarantined), len(exc.quarantined),
        )
        logger.error("Blocking data quality check failed, nothing was loaded: %s", exc)
        raise

    write_quarantine(quarantined, paths["quarantine_dir"])
    write_dq_report(results, paths["dq_report_dir"], len(df), len(good), len(quarantined))
    for r in results:
        if not r.passed and r.severity == "warn":
            logger.warning("DQ warning %s: %d rows. %s", r.name, r.failed_rows, r.details)
    passed = sum(1 for r in results if r.passed)
    logger.info(
        "DQ summary: %d/%d checks passed, %d rows quarantined", passed, len(results), len(quarantined)
    )
    write_parquet(good, paths["processed_dir"])
    return load(good, config, source=source)


def process(
    raw: list, config: dict, source: str, check_timeliness: bool, min_hours: int | None = None
) -> int:
    """Transform raw Open-Meteo records, then validate and load them."""
    wmo = pd.read_csv(config["paths"]["wmo_codes"])
    df = transform(raw, wmo)
    return process_frame(df, config, source, check_timeliness, min_hours)


def incremental_starts(config: dict, now: datetime | None = None) -> dict:
    """Work out, per city, the date to request from: the watermark minus an overlap."""
    now = now or datetime.now(timezone.utc)
    db_path = Path(config["paths"]["database"])
    if not db_path.exists():
        return {}
    conn = connect(db_path)
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "fact_weather_hourly" not in tables:
            return {}
        marks = get_watermarks(conn, FORECAST_SOURCE, now)
    finally:
        conn.close()
    overlap = timedelta(hours=config["incremental"]["overlap_hours"])
    return {city: (mark - overlap).date() for city, mark in marks.items()}


def run(config: dict) -> int:
    """Incremental run: fetch only from each city's watermark onwards, then load."""
    starts = incremental_starts(config)
    if starts:
        logger.info("Incremental run, request starts: %s", {k: str(v) for k, v in starts.items()})
    else:
        logger.info("No watermark found, falling back to yesterday and today")
    raw = extract(config, starts=starts)
    if not raw:
        logger.error("Nothing was extracted, so nothing will be loaded")
        return 0
    return process(raw, config, FORECAST_SOURCE, check_timeliness=True)


def backfill(
    config: dict, days: int | None = None, start: date | None = None, end: date | None = None
) -> int:
    """Backfill history from the archive API. Ends at today minus lag_days by default."""
    lag = config["backfill"]["lag_days"]
    end = end or (datetime.now(timezone.utc).date() - timedelta(days=lag))
    start = start or (end - timedelta(days=(days or 30) - 1))
    logger.info("Backfilling %s to %s", start, end)
    raw = extract_archive(config, start, end)
    if not raw:
        logger.error("Nothing was extracted, so nothing will be loaded")
        return 0
    return process(raw, config, ARCHIVE_SOURCE, check_timeliness=False, min_hours=1)


def run_weatherapi(config: dict) -> int:
    """Load WeatherAPI data through the same validate and load path as Open-Meteo."""
    raw = extract_weatherapi(config)
    if not raw:
        logger.error("Nothing was extracted from WeatherAPI, so nothing will be loaded")
        raise RuntimeError("WeatherAPI extract failed for every city")
    codes = pd.read_csv(config["paths"]["weatherapi_codes"])
    wmo = pd.read_csv(config["paths"]["wmo_codes"])
    frame = pd.concat([normalise_weatherapi(p, c, codes) for c, p in raw], ignore_index=True)
    df = transform_canonical(frame, wmo)
    return process_frame(df, config, WEATHERAPI_SOURCE, check_timeliness=False, min_hours=1)