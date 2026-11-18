"""Create tests/fixtures/open_meteo_london.json from the newest real London response, trimmed to 6 hours."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
candidates = sorted((root / "data" / "raw").glob("*/London_*.json"), reverse=True)
for path in candidates:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "is_day" in payload["hourly"]:
        break
else:
    raise SystemExit("No raw London file with is_day found. Run: python -m weatherflow run")

payload["hourly"] = {key: values[:6] for key, values in payload["hourly"].items()}
out = root / "tests" / "fixtures" / "open_meteo_london.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print("Wrote", out, "from", path.name)