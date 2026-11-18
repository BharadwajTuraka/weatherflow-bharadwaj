-- Q1: How much data do we hold per city, and what period does it cover? (join)
SELECT c.city_name, COUNT(*) AS row_count,
       MIN(f.observed_at_utc) AS first_obs, MAX(f.observed_at_utc) AS last_obs
FROM fact_weather_hourly f
JOIN dim_city c ON c.city_id = f.city_id
GROUP BY c.city_name
ORDER BY c.city_name;

-- Q2: What was the average temperature in each city yesterday (London date)? (join)
SELECT c.city_name, ROUND(AVG(f.temperature_c), 1) AS avg_temp_c
FROM fact_weather_hourly f
JOIN dim_city c ON c.city_id = f.city_id
JOIN dim_date d ON d.date_id = f.date_id
WHERE d.full_date = date('now', '-1 day')
GROUP BY c.city_name
ORDER BY avg_temp_c DESC;

-- Q3: Which 5 hours had the strongest wind across all cities? (join)
SELECT c.city_name, f.observed_at_utc, f.wind_speed_kmh, f.beaufort_scale
FROM fact_weather_hourly f
JOIN dim_city c ON c.city_id = f.city_id
ORDER BY f.wind_speed_kmh DESC
LIMIT 5;

-- Q4: Average wind speed by city on weekends vs weekdays (two joins)
SELECT c.city_name,
       CASE WHEN d.is_weekend = 1 THEN 'weekend' ELSE 'weekday' END AS day_type,
       ROUND(AVG(f.wind_speed_kmh), 1) AS avg_wind_kmh,
       COUNT(*) AS hours
FROM fact_weather_hourly f
JOIN dim_city c ON c.city_id = f.city_id
JOIN dim_date d ON d.date_id = f.date_id
GROUP BY c.city_name, day_type
ORDER BY c.city_name, day_type;

-- Q5: How many hours of each outdoor work risk level per city? (join)
SELECT c.city_name, f.outdoor_work_risk, COUNT(*) AS hours
FROM fact_weather_hourly f
JOIN dim_city c ON c.city_id = f.city_id
GROUP BY c.city_name, f.outdoor_work_risk
ORDER BY c.city_name, f.outdoor_work_risk;