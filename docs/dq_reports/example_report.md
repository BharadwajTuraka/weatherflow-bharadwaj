# Data quality report 2026-11-18 09:23:38 UTC

- Rows in: 240
- Rows passed: 240
- Rows quarantined: 0

| Check | Dimension | Severity | Result | Failed | Details |
|---|---|---|---|---|---|
| missing_required_field | completeness | quarantine | PASS | 0 | city, observed_at_utc and temperature_c must not be null |
| temperature_out_of_range | validity | quarantine | PASS | 0 | temperature_c between -30 and 45 |
| humidity_out_of_range | validity | quarantine | PASS | 0 | humidity_pct between 0 and 100 |
| negative_precipitation_or_wind | validity | quarantine | PASS | 0 | precipitation_mm and wind_speed_kmh must be >= 0 |
| feels_like_consistency | consistency | warn | PASS | 0 | feels_like_c within 15 C of temperature_c |
| known_weather_code | validity | warn | PASS | 0 | weather_code must exist in the WMO reference table |
| unique_keys | uniqueness | fail | PASS | 0 | no duplicate ('city', 'observed_at_utc') |
| expected_hours_per_city | completeness | fail | PASS | 0 | every city has at least 24 hours |
| data_freshness | timeliness | warn | PASS | 0 | latest past observation is 0.4 h old (limit 3 h) |
