"""Extract: call the weather API (with retries) and land raw JSON."""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


def fetch_city(city: dict, api_cfg: dict) -> dict:
    """Fetch forecast JSON for one city. Retry timeouts, connection errors and 5xx only."""
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": ",".join(api_cfg["hourly_variables"]),
        "past_days": 1,
        "forecast_days": 1,
        "timezone": api_cfg["timezone"],
    }
    max_retries = api_cfg["max_retries"]
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                api_cfg["forecast_url"], params=params, timeout=api_cfg["timeout_seconds"]
            )
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as exc:
            error = exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and status < 500:
                logger.error("%s: HTTP %s is a client error, not retrying", city["name"], status)
                raise
            error = exc
        if attempt < max_retries:
            wait = 2 ** attempt
            logger.warning(
                "%s: %s. Retry %d of %d in %ss",
                city["name"], error, attempt + 1, max_retries, wait,
            )
            time.sleep(wait)
    raise error


def save_raw(city_name: str, payload: dict, raw_dir: Path) -> Path:
    """Save the API response unchanged to raw_dir/<date>/<city>_<timestamp>.json."""
    now = datetime.now(timezone.utc)
    folder = Path(raw_dir) / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{city_name}_{now.strftime('%Y%m%dT%H%M%S')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def extract(config: dict) -> list[tuple[str, dict]]:
    """Fetch and land raw data for every configured city. One failure does not stop the rest."""
    results = []
    for city in config["cities"]:
        try:
            payload = fetch_city(city, config["api"])
            path = save_raw(city["name"], payload, config["paths"]["raw_dir"])
            logger.info(
                "%s: %d hourly records saved to %s",
                city["name"], len(payload["hourly"]["time"]), path,
            )
            results.append((city["name"], payload))
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s: %s", city["name"], exc)
    return results