"""Cross-source check: do two weather sources agree about the temperature?"""
import sqlite3
from pathlib import Path

import pandas as pd


def cross_source_report(db_path: Path, threshold_c: float) -> dict:
    """Compare Open-Meteo and WeatherAPI temperatures for the same city and hour.

    Returns the number of hours compared, how many differ by more than the threshold,
    and the city with the largest average gap. This is a warning, not a blocking check.
    """
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT c.city_name AS city, f.observed_at_utc, f.source, f.temperature_c "
            "FROM fact_weather_hourly f JOIN dim_city c ON c.city_id = f.city_id "
            "WHERE f.source IN ('open_meteo_forecast', 'weatherapi_forecast')",
            conn,
        )
    finally:
        conn.close()
    wide = df.pivot_table(
        index=["city", "observed_at_utc"], columns="source", values="temperature_c"
    )
    if "open_meteo_forecast" not in wide.columns or "weatherapi_forecast" not in wide.columns:
        return {"compared": 0, "disagreements": 0, "worst_city": None, "threshold_c": threshold_c}
    wide = wide.dropna()
    if wide.empty:
        return {"compared": 0, "disagreements": 0, "worst_city": None, "threshold_c": threshold_c}
    wide["gap"] = (wide["open_meteo_forecast"] - wide["weatherapi_forecast"]).abs()
    by_city = wide.groupby("city")["gap"].mean()
    return {
        "compared": int(len(wide)),
        "disagreements": int((wide["gap"] > threshold_c).sum()),
        "worst_city": str(by_city.idxmax()),
        "worst_city_mean_gap_c": round(float(by_city.max()), 2),
        "threshold_c": threshold_c,
    }