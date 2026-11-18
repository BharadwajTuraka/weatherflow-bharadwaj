"""Command-line entry point: python -m weatherflow run | backfill"""
import argparse
import logging
import sys
from datetime import date

from weatherflow.config import load_config
from weatherflow.pipeline import backfill, run
from weatherflow.validate import DataQualityError


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the chosen command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(prog="weatherflow")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Incremental run: fetch recent data, validate and load")
    back = sub.add_parser("backfill", help="Load history from the archive API")
    back.add_argument("--days", type=int, default=30, help="Number of days ending at today minus the API lag")
    back.add_argument("--start-date", type=date.fromisoformat, help="First date, YYYY-MM-DD")
    back.add_argument("--end-date", type=date.fromisoformat, help="Last date, YYYY-MM-DD")
    args = parser.parse_args(argv)

    config = load_config()
    try:
        if args.command == "run":
            run(config)
        elif args.command == "backfill":
            backfill(config, days=args.days, start=args.start_date, end=args.end_date)
    except DataQualityError:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())