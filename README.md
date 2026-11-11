# weatherflow-bharadwaj
# WeatherFlow (Bharadwaj)

Goal: one command pulls live weather for 5 UK cities (London, Manchester, Birmingham, Edinburgh, Cardiff) from the Open-Meteo API, saves the raw data, cleans it, and loads it into a SQLite database that can be queried with SQL.

## How to set up

    git clone https://github.com/BharadwajTuraka/weatherflow-bharadwaj.git
    cd weatherflow-bharadwaj
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

Author: Bharadwaj Turaka
End

## How to run the pipeline

    python etl_v1.py

This extracts weather for 5 UK cities, saves raw JSON in data/raw/, cleans it, and loads it into weather.db (table weather_hourly). Running it twice does not create duplicates.

Check the result:

    python -c "import sqlite3; print(sqlite3.connect('weather.db').execute('SELECT city, COUNT(*) FROM weather_hourly GROUP BY city').fetchall())"

Example output: 5 cities with 48 rows each.
