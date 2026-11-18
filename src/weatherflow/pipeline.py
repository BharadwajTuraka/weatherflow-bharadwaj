"""Wire extract, transform and load together."""
import logging

import pandas as pd

from weatherflow.extract import extract
from weatherflow.load import load, write_parquet
from weatherflow.transform import transform

logger = logging.getLogger(__name__)


def run(config: dict) -> int:
    """Run the full pipeline and return the number of rows loaded."""
    raw = extract(config)
    if not raw:
        logger.error("Nothing was extracted, so nothing will be loaded")
        return 0
    wmo = pd.read_csv(config["paths"]["wmo_codes"])
    df = transform(raw, wmo)
    write_parquet(df, config["paths"]["processed_dir"])
    return load(df, config["paths"]["database"])