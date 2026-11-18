"""Load and validate config.yaml."""
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# src/weatherflow/config.py -> project root
CONFIG_FILE = Path(__file__).resolve().parents[2] / "config.yaml"

REQUIRED = {
    "api": ["forecast_url", "timeout_seconds", "max_retries", "hourly_variables", "timezone"],
    "paths": ["raw_dir", "processed_dir", "quarantine_dir", "database", "wmo_codes", "schema_sql"],
}


def load_config(path: Path = CONFIG_FILE) -> dict:
    """Read config.yaml, check required keys, and make all paths absolute."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} is empty or not valid YAML")
    for section, keys in REQUIRED.items():
        if section not in raw:
            raise ValueError(f"config.yaml is missing the '{section}' section")
        for key in keys:
            if key not in raw[section]:
                raise ValueError(f"config.yaml is missing '{section}.{key}'")
    if not raw.get("cities"):
        raise ValueError("config.yaml must list at least one city")
    root = path.parent
    raw["paths"] = {key: (root / value).resolve() for key, value in raw["paths"].items()}
    logger.info("Loaded config from %s", path)
    return raw