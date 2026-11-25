# ADR 0002: Store times in UTC and display them in Europe/London

- **Status:** Accepted
- **Date:** 2026-11-25
- **Author:** Bharadwaj Turaka

## Context
When the clocks change, 01:00 London time happens twice, so local time can create duplicate or null timestamps. The business plans by UK calendar day.

## Decision
We will request UTC from the API, store `observed_at_utc`, and convert to Europe/London only for display and for the business date (`date_id`).

## Consequences
- **Good:** no ambiguous hours, and a safe primary key.
- **Bad:** every display layer must convert the time.
- **Follow-up:** keep the conversion in one helper in the dashboard.

## Alternatives considered
| Option | Why not chosen |
| :---- | :---- |
| Store local time | Breaks on the autumn clock change |
| Show UTC to users | Confusing for UK staff |

## Evidence
`test_fact_date_is_the_london_local_date` in `tests/test_load.py`.