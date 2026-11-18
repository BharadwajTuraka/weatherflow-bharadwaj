"""Demo: inject bad data and show the checks react."""
import glob

import pandas as pd

from weatherflow.config import load_config
from weatherflow.validate import DataQualityError, validate

config = load_config()
pattern = str(config["paths"]["processed_dir"] / "weather_hourly" / "*" / "*.parquet")
df = pd.read_parquet(sorted(glob.glob(pattern))[-1])
cities = [c["name"] for c in config["cities"]]
dq = config["dq"]

# 1) A 99 C reading should be quarantined, not loaded
hot = df.iloc[[0]].copy()
hot["temperature_c"] = 99.0
hot["observed_at_utc"] = hot["observed_at_utc"] + pd.Timedelta(hours=500)
good, bad, results = validate(pd.concat([df, hot], ignore_index=True), dq, cities)
print("Rows kept:", len(good), "| quarantined:", len(bad))
print(bad[["city", "temperature_c", "dq_failure_reason"]])

# 2) A duplicate row should fail the whole run
dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
try:
    validate(dup, dq, cities)
    print("ERROR: the duplicate was not detected")
except DataQualityError as exc:
    print("Run failed as expected:", exc)