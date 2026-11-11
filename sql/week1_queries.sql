-- Q1: How much data do we hold per city, and what period does it cover?
SELECT city, COUNT(*) AS row_count, MIN(observed_at) AS first_obs, MAX(observed_at) AS last_obs
FROM weather_hourly
GROUP BY city;

-- Q2: What was the average temperature in each city yesterday?
SELECT city, ROUND(AVG(temperature_c), 1) AS avg_temp_c
FROM weather_hourly
WHERE date(observed_at) = date('now', '-1 day')
GROUP BY city;

-- Q3: Which 5 hours had the strongest wind across all cities?
SELECT city, observed_at, wind_speed_kmh
FROM weather_hourly
ORDER BY wind_speed_kmh DESC
LIMIT 5;