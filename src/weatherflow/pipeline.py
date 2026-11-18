"""Wire extract, transform, validate and load together."""
import logging

import pandas as pd

from weatherflow.extract import extract
from weatherflow.load import load, write_parquet
from weatherflow.transform import transform
from weatherflow.validate import DataQualityError, validate, write_dq_report, write_quarantine

logger = logging.getLogger(__name__)


def run(config: dict) -> int:
    """Run the full pipeline and return the number of rows loaded."""
    paths = config["paths"]
    raw = extract(config)
    if not raw:
        logger.error("Nothing was extracted, so nothing will be loaded")
        return 0
    wmo = pd.read_csv(paths["wmo_codes"])
    df = transform(raw, wmo)

    cities = [c["name"] for c in config["cities"]]
    try:
        good, quarantined, results = validate(df, config["dq"], cities)
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
    return load(good, config)