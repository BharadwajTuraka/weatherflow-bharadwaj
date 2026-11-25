"""Streamlit dashboard: where is outdoor work risky in the next 24 hours?"""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "weather.db"
REPORT_DIR = Path(__file__).resolve().parents[1] / "docs" / "dq_reports"
RISK_WORDS = {"high": "HIGH", "medium": "Medium", "low": "Low"}
RISK_COLOURS = {"high": "#f8d7da", "medium": "#fff3cd", "low": "#d4edda"}

st.set_page_config(page_title="WeatherFlow", layout="wide")


@st.cache_data(ttl=300)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run a parameterised query and cache the result for 5 minutes."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def to_london(series: pd.Series) -> pd.Series:
    """Convert UTC timestamps to Europe/London for display."""
    return pd.to_datetime(series, utc=True).dt.tz_convert("Europe/London")


st.title("WeatherFlow: outdoor work risk")
st.caption("Where is outdoor work risky in the next 24 hours?")

if not DB_PATH.exists():
    st.error("No database found. Run: python -m weatherflow run")
    st.stop()

# Freshness and data quality
latest = query("SELECT MAX(ingested_at_utc) AS latest FROM fact_weather_hourly")
if latest.empty or latest.loc[0, "latest"] is None:
    st.warning("The warehouse has no data yet.")
    st.stop()
loaded = to_london(pd.Series([latest.loc[0, "latest"]])).iloc[0]
age_hours = (pd.Timestamp.now(tz="Europe/London") - loaded).total_seconds() / 3600
st.markdown(f"**Data as of {loaded:%d %b %Y %H:%M} UK time** ({age_hours:.1f} hours ago)")
if age_hours > 3:
    st.warning(f"Data is {age_hours:.1f} hours old. Risk levels below may be out of date.")

reports = sorted(REPORT_DIR.glob("2*.md")) if REPORT_DIR.exists() else []
if reports:
    lines = reports[-1].read_text(encoding="utf-8").splitlines()
    summary = [ln.lstrip("- ") for ln in lines if ln.startswith("- Rows")]
    st.caption("Latest data quality report: " + " | ".join(summary))

# Next 24 hours
st.header("Next 24 hours")
now_utc = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M")
end_utc = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
nxt = query(
    "SELECT c.city_name, f.observed_at_utc, f.outdoor_work_risk, f.beaufort_scale, "
    "f.precipitation_mm, f.weather_category "
    "FROM fact_weather_hourly f JOIN dim_city c ON c.city_id = f.city_id "
    "WHERE f.observed_at_utc >= ? AND f.observed_at_utc <= ? "
    "AND f.source = 'open_meteo_forecast' ORDER BY f.observed_at_utc",
    (now_utc, end_utc),
)
if nxt.empty:
    st.info("No forecast hours in the next 24 hours. Run the pipeline to refresh.")
else:
    nxt["hour"] = to_london(nxt["observed_at_utc"]).dt.strftime("%H:%M")
    nxt["risk"] = nxt["outdoor_work_risk"].map(RISK_WORDS)
    summary_rows = []
    for city, group in nxt.groupby("city_name"):
        worst = group["outdoor_work_risk"].map({"low": 0, "medium": 1, "high": 2}).max()
        level = {0: "Low", 1: "Medium", 2: "HIGH"}[worst]
        high_hours = group[group["outdoor_work_risk"] == "high"]["hour"].tolist()
        detail = "High risk at " + ", ".join(high_hours) if high_hours else "No high-risk hours"
        summary_rows.append({"City": city, "Worst risk": level, "Details": detail})
    st.dataframe(pd.DataFrame(summary_rows), hide_index=True, width="stretch")

    grid = nxt.pivot(index="hour", columns="city_name", values="risk")
    st.caption("Risk by hour (words, not just colour)")
    st.dataframe(grid, width="stretch")

# 7-day trend
st.header("Last 7 days")
trend = query(
    "SELECT c.city_name, f.observed_at_utc, f.temperature_c, f.wind_speed_kmh "
    "FROM fact_weather_hourly f JOIN dim_city c ON c.city_id = f.city_id "
    "WHERE f.observed_at_utc >= ? ORDER BY f.observed_at_utc",
    ((pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)).strftime("%Y-%m-%dT%H:%M"),),
)
if trend.empty:
    st.info("No data for the last 7 days.")
else:
    trend["time"] = to_london(trend["observed_at_utc"]).dt.tz_localize(None)
    left, right = st.columns(2)
    with left:
        st.subheader("Temperature (C)")
        st.line_chart(trend.pivot_table(index="time", columns="city_name", values="temperature_c"))
    with right:
        st.subheader("Wind speed (km/h)")
        st.line_chart(trend.pivot_table(index="time", columns="city_name", values="wind_speed_kmh"))

# Sources
st.header("Data sources")
src = query("SELECT source, COUNT(*) AS rows_loaded FROM fact_weather_hourly GROUP BY source")
st.dataframe(src, hide_index=True)
st.caption("Only Open-Meteo is connected so far. A second source (WeatherAPI) is planned.")
