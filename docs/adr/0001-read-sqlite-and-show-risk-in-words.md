# ADR 0001: The dashboard reads SQLite and shows risk in words

- **Status:** Accepted
- **Date:** 2026-11-25
- **Author:** Bharadwaj Turaka

## Context
The client asks one question: where is outdoor work risky in the next 24 hours? Docker was not installed on my machine, so the PostgreSQL warehouse (Task 3.2) was not available. The star schema already exists in SQLite from Week 2.

## Decision
We will build the Streamlit dashboard on the existing SQLite database, show risk as the words Low, Medium and HIGH (not colour alone), and warn when data is more than 3 hours old.

## Consequences
- **Good:** the dashboard works today and uses the same star schema.
- **Bad:** SQLite allows one writer and no network access, so this is not production-ready.
- **Follow-up:** point the dashboard at PostgreSQL through DATABASE_URL once Docker is available.

## Alternatives considered
| Option | Why not chosen |
| :---- | :---- |
| Wait for PostgreSQL | Docker was not available and the deadline is fixed |
| Colour-only risk cells | Not accessible and not clear for colour-blind users |

## Evidence
Dashboard screenshot in the pull request for `feature/dashboard`.