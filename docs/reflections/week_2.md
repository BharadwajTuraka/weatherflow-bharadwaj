# Week 2 reflection

## What I built
A weatherflow package with config, logging and retries, a transform layer with Parquet output, a star schema with an idempotent load, data quality checks with quarantine, 77 tests at 99% coverage, and backfill and incremental loads.

## What was hard
Pasted files being cut off, a test that assumed the wrong dates, and the watermark logic.

## What I learned
Why loads must be safe to re-run, why raw data is saved first, and why the API is mocked in tests.

## What I would do differently
Check for unsaved files before running, and start the tests earlier.

## Review
My partner's review of my PR is still pending.