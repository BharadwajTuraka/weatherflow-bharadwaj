import json
from datetime import datetime, timezone
from pathlib import Path
import requests

BASE_URL = "https://api.open-meteo.com/v1/forecast"
CITIES = [
    {"name": "London",     "latitude": 51.5085, "longitude": -0.1257},
    {"name": "Manchester", "latitude": 53.4809, "longitude": -2.2374},
    {"name": "Birmingham", "latitude": 52.4814, "longitude": -1.8998},
    {"name": "Edinburgh",  "latitude": 55.9521, "longitude": -3.1965},
    {"name": "Cardiff",    "latitude": 51.4802, "longitude": -3.1792},
]

def fetch_city(city: dict) -> dict:
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                  "precipitation,wind_speed_10m,weather_code",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Europe/London",
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def save_raw(city_name: str, payload: dict) -> Path:
    now = datetime.now(timezone.utc)
    folder = Path("data/raw") / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{city_name}_{now.strftime('%Y%m%dT%H%M%S')}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path

def extract(cities=CITIES) -> list[tuple[str, dict]]:
    results = []
    for city in cities:
        try:
            payload = fetch_city(city)
            path = save_raw(city["name"], payload)
            print(f"{city['name']}: {len(payload['hourly']['time'])} records -> {path}")
            results.append((city["name"], payload))
        except requests.RequestException as e:
            print(f"ERROR for {city['name']}: {e}")
    return results

if __name__ == "__main__":
    extract()