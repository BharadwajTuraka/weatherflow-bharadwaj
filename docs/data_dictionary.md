# Data Dictionary: weather_hourly

**Source:** Open-Meteo Forecast API, https://api.open-meteo.com/v1/forecast
**Licence:** Open-Meteo data is CC BY 4.0 (attribution required)
**Refresh frequency:** Hourly data, pulled on demand by running `python etl_v1.py`
**Grain:** One row per city per hour
**Primary key:** (city, observed_at)
**Time zone:** Europe/London local time (requested with `timezone=Europe/London`)

| Column | Type | Unit | Description | Example | Nullable? | Source |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| city | TEXT | n/a | City name (London, Manchester, Birmingham, Edinburgh, Cardiff) | London | No | CITIES list in extract.py |
| observed_at | TEXT (ISO 8601) | Europe/London local time | Start of the hourly period | 2026-11-10T14:00 | No | Open-Meteo `hourly.time` |
| temperature_c | REAL | °C | Air temperature 2 m above ground | 7.3 | Yes | Open-Meteo `temperature_2m` |
| feels_like_c | REAL | °C | Apparent temperature (wind chill and humidity included) | 4.6 | Yes | Open-Meteo `apparent_temperature` |
| humidity_pct | INTEGER | % | Relative humidity 2 m above ground | 85 | Yes | Open-Meteo `relative_humidity_2m` |
| precipitation_mm | REAL | mm | Total precipitation in the preceding hour | 0.0 | Yes | Open-Meteo `precipitation` |
| wind_speed_kmh | REAL | km/h | Wind speed 10 m above ground | 10.8 | Yes | Open-Meteo `wind_speed_10m` |
| weather_code | INTEGER | WMO code | Weather condition (0 clear, 3 overcast, 51 light drizzle, 61 slight rain) | 3 | Yes | Open-Meteo `weather_code` |
| ingested_at_utc | TEXT (ISO 8601) | UTC | When the pipeline run loaded the row | 2026-11-11T00:51:27+00:00 | No | Added by `etl_v1.py` |