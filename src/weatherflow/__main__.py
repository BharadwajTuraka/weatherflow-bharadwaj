"""Command-line entry point: python -m weatherflow run"""
import argparse
import logging
import sys

from weatherflow.config import load_config
from weatherflow.pipeline import run
from weatherflow.validate import DataQualityError


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the chosen command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(prog="weatherflow")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Extract, transform, validate and load weather data")
    args = parser.parse_args(argv)

    config = load_config()
    if args.command == "run":
        try:
            run(config)
        except DataQualityError:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())