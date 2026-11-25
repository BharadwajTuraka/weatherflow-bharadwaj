![CI](https://github.com/BharadwajTuraka/weatherflow-bharadwaj/actions/workflows/ci.yml/badge.svg)
Goal: one command pulls live weather for 5 UK cities (London, Manchester, Birmingham, Edinburgh, Cardiff) from the Open-Meteo API, saves the raw data, cleans it, and loads it into a SQLite database that can be queried with SQL.

## How to set up

    git clone https://github.com/BharadwajTuraka/weatherflow-bharadwaj.git
    cd weatherflow-bharadwaj
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    pip install -e .

Author: Bharadwaj Turaka

## How to run the pipeline

## How to run the pipeline

```
python -m weatherflow run
```

This extracts weather for 5 UK cities, saves raw JSON in data/raw/, cleans it, and loads it into data/weather.db (table weather_hourly). Running it twice does not create duplicates.

Check the result:

```
python -c "import sqlite3; print(sqlite3.connect('data/weather.db').execute('SELECT city, COUNT(*) FROM weather_hourly GROUP BY city').fetchall())"
```

Example output: 5 cities with 48 rows each.

## Running the tests

```
pip install -e .
pytest -v --cov=src --cov-report=term-missing
```

Tests mock the API, so they run offline. Coverage summary from the last run:

```
TOTAL    303    4    99%
72 passed
```