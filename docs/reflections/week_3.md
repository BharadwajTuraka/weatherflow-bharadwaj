# Week 3 reflection

## What I built
- CI with GitHub Actions: tests and a 70% coverage gate on every push and PR. PR #7 shows a deliberately broken test failing (red) and then passing (green). A CI badge is in the README.
- A Streamlit dashboard on the SQLite warehouse showing the next 24 hours of outdoor work risk in words, a 7-day trend, data freshness and the data quality summary.
- Three architecture decision records in docs/adr/.
- A second source (WeatherAPI) loaded through the same transform, validate and load path with source weatherapi_forecast. The key lives only in .env, .env.example is committed with a fake value, and a missing key stops the run with exit code 1 and no request sent. A cross-source temperature check warns when the two sources differ by more than 3 C (threshold in config.yaml).
- 87 tests passing, all offline.

## What I did not do, and why
Docker was not installed on my machine, so I did not do Task 3.2 (PostgreSQL warehouse), Task 3.3 (Docker image) or Task 3.4 (Airflow). The dashboard therefore reads SQLite, and the PostgreSQL integration test in CI is still to do. I also did not build the alerts command. I recorded these choices in ADRs 0001 and 0003.

## What was hard
Pasted code files were cut off several times, and I edited the wrong file once because two files were both called extract.py. I fixed these by checking the breadcrumb before pasting, saving before running, and replacing whole files. A placeholder in .env caused HTTP 401 errors until I found it with a status and key length check.

## What I learned
Secrets stay in .env and never in Git. Exit codes must be non-zero on failure so schedulers can see it. A second source should reuse the same pipeline instead of copying it. CI catches mistakes before they reach main.

## What I would do differently
Install Docker in the first week, start the heavy tasks earlier, and write tests as I build.