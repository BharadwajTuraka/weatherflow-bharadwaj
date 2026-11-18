"""Run every query in sql/analysis_queries.sql and print the results."""
import sqlite3

conn = sqlite3.connect("data/weather.db")
text = open("sql/analysis_queries.sql", encoding="utf-8").read()
for number, statement in enumerate(text.split(";"), start=1):
    if not statement.strip():
        continue
    print(f"--- Query {number} ---")
    for row in conn.execute(statement):
        print(row)