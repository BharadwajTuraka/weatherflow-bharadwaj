"""Normalise: turn each source's raw JSON into the same canonical table."""
import pandas as pd

CANONICAL = [
    "city", "observed_at_utc", "temperature_c", "feels_like_c", "humidity_pct",
    "precipitation_mm", "wind_speed_kmh", "weather_code", "is_daylight",
]


def normalise_open_meteo(payload: dict, city: str) -> pd.DataFrame:
    """Turn an Open-Meteo response into canonical columns (hourly, UTC)."""
    hourly = pd.DataFrame(payload["hourly"])
    return pd.DataFrame({
        "city": city,
        "observed_at_utc": pd.to_datetime(hourly["time"], utc=True),
        "temperature_c": hourly["temperature_2m"],
        "feels_like_c": hourly["apparent_temperature"],
        "humidity_pct": hourly["relative_humidity_2m"],
        "precipitation_mm": hourly["precipitation"],
        "wind_speed_kmh": hourly["wind_speed_10m"],
        "weather_code": hourly["weather_code"],
        "is_daylight": hourly["is_day"].astype(bool),
    })[CANONICAL]


def normalise_weatherapi(payload: dict, city: str, codes: pd.DataFrame) -> pd.DataFrame:
    """Turn a WeatherAPI response into canonical columns.

    Time comes from time_epoch (Unix seconds, UTC). WeatherAPI condition codes are mapped
    to the WMO-style code stored for the same category, so the shared transform can run.
    """
    rows = []
    for day in payload["forecast"]["forecastday"]:
        for hour in day["hour"]:
            rows.append({
                "city": city,
                "observed_at_utc": pd.to_datetime(hour["time_epoch"], unit="s", utc=True),
                "temperature_c": hour["temp_c"],
                "feels_like_c": hour["feelslike_c"],
                "humidity_pct": hour["humidity"],
                "precipitation_mm": hour["precip_mm"],
                "wind_speed_kmh": hour["wind_kph"],
                "weather_api_code": hour["condition"]["code"],
                "is_daylight": bool(hour["is_day"]),
            })
    df = pd.DataFrame(rows)
    category_to_wmo = {
        "clear": 0, "cloudy": 3, "fog": 45, "drizzle": 51, "rain": 61, "snow": 71, "storm": 95,
    }
    lookup = codes.set_index("code")["category"]
    categories = df["weather_api_code"].map(lookup)
    df["weather_code"] = categories.map(category_to_wmo).fillna(-1).astype(int)
    return df[CANONICAL]