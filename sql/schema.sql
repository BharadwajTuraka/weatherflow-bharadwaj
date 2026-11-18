-- Star schema for hourly weather.
-- Grain of fact_weather_hourly: one row per city, per hour, per source.

CREATE TABLE IF NOT EXISTS dim_city (
    city_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name  TEXT NOT NULL UNIQUE,
    country    TEXT NOT NULL,
    latitude   REAL NOT NULL,
    longitude  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id      INTEGER PRIMARY KEY,          -- YYYYMMDD
    full_date    TEXT NOT NULL,
    day_of_week  TEXT NOT NULL,
    is_weekend   INTEGER NOT NULL CHECK (is_weekend IN (0, 1)),
    month        INTEGER NOT NULL,
    year         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_weather_hourly (
    city_id              INTEGER NOT NULL REFERENCES dim_city (city_id),
    date_id              INTEGER NOT NULL REFERENCES dim_date (date_id),  -- London local date
    observed_at_utc      TEXT    NOT NULL,
    hour_local           INTEGER NOT NULL,
    temperature_c        REAL,
    temperature_f        REAL,
    feels_like_c         REAL,
    humidity_pct         INTEGER,
    precipitation_mm     REAL,
    wind_speed_kmh       REAL,
    wind_speed_ms        REAL,
    beaufort_scale       INTEGER,
    weather_code         INTEGER,
    weather_description  TEXT,
    weather_category     TEXT,
    is_daylight          INTEGER,
    outdoor_work_risk    TEXT NOT NULL CHECK (outdoor_work_risk IN ('low', 'medium', 'high')),
    source               TEXT NOT NULL,
    ingested_at_utc      TEXT NOT NULL,
    PRIMARY KEY (city_id, observed_at_utc, source)
);