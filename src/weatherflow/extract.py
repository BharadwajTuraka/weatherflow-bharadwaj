"""Extract: call the weather API (with retries) and land raw JSON."""
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def _get_with_retries(url: str, params: dict, label: str, api_cfg: dict) -> dict:
    """GET JSON. Retry timeouts, connection errors and 5xx only."""
    max_retries = api_cfg["max_retries"]
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=api_cfg["timeout_seconds"])
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as exc:
            error = exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and status < 500:
                logger.error("%s: HTTP %s is a client error, not retrying", label, status)
                raise
            error = exc
        if attempt < max_retries:
            wait = 2 ** attempt
            logger.warning("%s: %s. Retry %d of %d in %ss", label, error, attempt + 1, max_retries, wait)
            time.sleep(wait)
    raise error


def fetch_city(city: dict, api_cfg: dict) -> dict:
    """Fetch the default forecast window (yesterday and today) for one city."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api_cfg["hourly_variables"]),
        "past_days": 1,
        "forecast_days": 1,
        "timezone": api_cfg["timezone"],
    }
    return _get_with_retries(api_cfg["forecast_url"], params, city["name"], api_cfg)


def fetch_forecast_from(city: dict, api_cfg: dict, start_date: date) -> dict:
    """Fetch the forecast API from start_date to the end of today (used by incremental runs)."""
    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api_cfg["hourly_variables"]),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": api_cfg["timezone"],
    }
    logger.info("%s: requesting %s to %s", city["name"], params["start_date"], params["end_date"])
    return _get_with_retries(api_cfg["forecast_url"], params, city["name"], api_cfg)


def fetch_archive(city: dict, api_cfg: dict, start_date: date, end_date: date) -> dict:
    """Fetch the historical archive API for one date range."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api_cfg["hourly_variables"]),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": api_cfg["timezone"],
    }
    label = f"{city['name']} {start_date}..{end_date}"
    return _get_with_retries(api_cfg["archive_url"], params, label, api_cfg)


def save_raw(city_name: str, payload: dict, raw_dir: Path, tag: str = "") -> Path:
    """Save the API response unchanged to raw_dir/<date>/<city>[_tag]_<timestamp>.json."""
    now = datetime.now(timezone.utc)
    folder = Path(raw_dir) / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    suffix = f"_{tag}" if tag else ""
    path = folder / f"{city_name}{suffix}_{now.strftime('%Y%m%dT%H%M%S%f')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def extract(config: dict, starts: dict | None = None) -> list[tuple[str, dict]]:
    """Fetch and land raw data for every configured city. One failure does not stop the rest.

    If starts maps a city name to a start date, only that city's recent window is requested
    (incremental). Otherwise the default window (yesterday and today) is used.
    """
    results = []
    for city in config["cities"]:
        try:
            start = (starts or {}).get(city["name"])
            if start is None:
                payload = fetch_city(city, config["api"])
            else:
                payload = fetch_forecast_from(city, config["api"], start)
            path = save_raw(city["name"], payload, config["paths"]["raw_dir"])
            logger.info(
                "%s: %d hourly records saved to %s",
                city["name"], len(payload["hourly"]["time"]), path,
            )
            results.append((city["name"], payload))
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s: %s", city["name"], exc)
    return results


def date_chunks(start: date, end: date, chunk_days: int) -> list[tuple[date, date]]:
    """Split start..end (inclusive) into consecutive ranges of at most chunk_days days."""
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


def extract_archive(config: dict, start: date, end: date) -> list[tuple[str, dict]]:
    """Backfill: fetch history in chunks per city, landing raw JSON for each chunk."""
    cfg = config["backfill"]
    results = []
    for city in config["cities"]:
        for chunk_start, chunk_end in date_chunks(start, end, cfg["chunk_days"]):
            try:
                payload = fetch_archive(city, config["api"], chunk_start, chunk_end)
                path = save_raw(city["name"], payload, config["paths"]["raw_dir"], tag="archive")
                logger.info(
                    "%s %s..%s: %d hourly records saved to %s",
                    city["name"], chunk_start, chunk_end, len(payload["hourly"]["time"]), path,
                )
                results.append((city["name"], payload))
            except requests.RequestException as exc:
                logger.error("Failed to fetch %s %s..%s: %s", city["name"], chunk_start, chunk_end, exc)
            time.sleep(cfg["sleep_seconds"])
    return results