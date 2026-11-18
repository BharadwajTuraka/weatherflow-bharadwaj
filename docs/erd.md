# Entity relationship diagram

**Grain:** one row per city, per hour, per source.

`fact_weather_hourly` holds the measurements. `dim_city` and `dim_date` describe them. `date_id` is the London (local) calendar date of the observation. The primary key `(city_id, observed_at_utc, source)` lets the load upsert safely, and `source` allows a second weather source later.

```mermaid
erDiagram
    dim_city ||--o{ fact_weather_hourly : "city_id"
    dim_date ||--o{ fact_weather_hourly : "date_id"

    dim_city {
        INTEGER city_id PK
        TEXT city_name
        TEXT country
        REAL latitude
        REAL longitude
    }
    dim_date {
        INTEGER date_id PK
        TEXT full_date
        TEXT day_of_week
        INTEGER is_weekend
        INTEGER month
        INTEGER year
    }
    fact_weather_hourly {
        INTEGER city_id FK
        INTEGER date_id FK
        TEXT observed_at_utc
        INTEGER hour_local
        REAL temperature_c
        REAL wind_speed_kmh
        INTEGER beaufort_scale
        TEXT weather_description
        TEXT outdoor_work_risk
        TEXT source
        TEXT ingested_at_utc
    }
```