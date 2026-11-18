"""Wire extract, transform and load together."""
import logging

from weatherflow.extract import extract
from weatherflow.load import load
from weatherflow.transform import transform

logger = logging.getLogger(__name__)


def run(config: dict) -> int:
    """Run the full pipeline and return the number of rows loaded."""
    raw = extract(config)
    if not raw:
        logger.error("Nothing was extracted, so nothing will be loaded")
        return 0
    df = transform(raw)
    return load(df, config["paths"]["database"])