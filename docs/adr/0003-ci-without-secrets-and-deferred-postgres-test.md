# ADR 0003: CI runs mocked tests with no secrets; the PostgreSQL test is deferred

- **Status:** Accepted
- **Date:** 2026-11-25
- **Author:** Bharadwaj Turaka

## Context
CI runs on every push and pull request. A real API key in CI would be a leak risk, and real API calls make tests slow and flaky. Docker was not available locally, so a PostgreSQL integration test could not be written and checked.

## Decision
We will run only mocked, offline tests in GitHub Actions with a 70% coverage gate, and add the PostgreSQL integration test when the warehouse exists.

## Consequences
- **Good:** CI is fast, free and secret-free. Coverage is currently 99%.
- **Bad:** the PostgreSQL load path is not yet tested in CI.
- **Follow-up:** add a test that loads the fixture into PostgreSQL twice and checks the row count.

## Alternatives considered
| Option | Why not chosen |
| :---- | :---- |
| Real API calls in CI | Needs a secret and is unreliable |
| Skip CI | A broken change could reach main |

## Evidence
Pull request #7 shows a red check, then a green check after the fix.