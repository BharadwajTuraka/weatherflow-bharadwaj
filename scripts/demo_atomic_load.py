"""Demo: a load that fails halfway leaves no partial rows."""
import glob

import pandas as pd

from weatherflow.config import load_config
from weatherflow.load import UPSERT_SQL, apply_schema, connect, to_fact_rows, upsert_cities

config = load_config()
pattern = str(config["paths"]["processed_dir"] / "weather_hourly" / "*" / "*.parquet")
df = pd.read_parquet(sorted(glob.glob(pattern))[-1])


def demo_rows(conn) -> int:
    """Count rows written by this demo."""
    return conn.execute(
        "SELECT COUNT(*) FROM fact_weather_hourly WHERE source = 'atomic_demo'"
    ).fetchone()[0]


conn = connect(config["paths"]["database"])
apply_schema(conn, config["paths"]["schema_sql"])
print("Demo rows before:", demo_rows(conn))
try:
    with conn:
        city_ids = upsert_cities(conn, config["cities"])
        rows = to_fact_rows(df, city_ids, "atomic_demo")
        conn.executemany(UPSERT_SQL, rows[:100])
        print("Inserted 100 rows inside the transaction. Now forcing an error...")
        raise RuntimeError("Simulated failure mid-load")
except RuntimeError as exc:
    print("Caught:", exc)
print("Demo rows after rollback:", demo_rows(conn))
conn.close()