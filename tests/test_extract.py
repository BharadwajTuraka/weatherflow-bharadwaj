"""Unit tests for extract, with the API mocked."""
import json

import pytest
import requests

from weatherflow.extract import extract, fetch_city, save_raw

API_CFG = {
    "forecast_url": "https://example.test/forecast",
    "timeout_seconds": 5,
    "max_retries": 3,
    "hourly_variables": ["temperature_2m"],
    "timezone": "UTC",
}
CITY = {"name": "London", "latitude": 51.5, "longitude": -0.12}


class FakeResponse:
    """A stand-in for requests.Response."""

    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return self._payload


@pytest.fixture
def sleeps(monkeypatch):
    """Replace time.sleep so tests are instant, and record the waits."""
    waits = []
    monkeypatch.setattr("weatherflow.extract.time.sleep", waits.append)
    return waits


def test_fetch_retries_on_server_errors_then_succeeds(monkeypatch, sleeps):
    responses = [FakeResponse(503), FakeResponse(503), FakeResponse(200, {"ok": True})]
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(args)
        return responses[len(calls) - 1]

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    assert fetch_city(CITY, API_CFG) == {"ok": True}
    assert len(calls) == 3
    assert sleeps == [1, 2]


def test_fetch_does_not_retry_a_404(monkeypatch, sleeps):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(args)
        return FakeResponse(404)

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    with pytest.raises(requests.HTTPError):
        fetch_city(CITY, API_CFG)
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("error_type", [requests.Timeout, requests.ConnectionError])
def test_fetch_retries_timeouts_and_connection_errors_then_gives_up(monkeypatch, sleeps, error_type):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(args)
        raise error_type("simulated")

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    with pytest.raises(error_type):
        fetch_city(CITY, API_CFG)
    assert len(calls) == 4  # first attempt plus 3 retries
    assert sleeps == [1, 2, 4]


def test_fetch_sends_the_configured_url_parameters_and_timeout(monkeypatch, sleeps):
    seen = {}

    def fake_get(url, params, timeout):
        seen.update(url=url, params=params, timeout=timeout)
        return FakeResponse(200, {"ok": True})

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    fetch_city(CITY, API_CFG)
    assert seen["url"] == "https://example.test/forecast"
    assert seen["params"]["hourly"] == "temperature_2m"
    assert seen["params"]["timezone"] == "UTC"
    assert seen["timeout"] == 5


def test_save_raw_writes_the_payload_unchanged(tmp_path):
    payload = {"hourly_units": {"temperature_2m": "°C"}, "hourly": {"time": ["2026-11-10T00:00"]}}
    path = save_raw("London", payload, tmp_path)
    assert path.exists()
    assert path.name.startswith("London_")
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_extract_continues_when_one_city_fails(monkeypatch, tmp_path, sleeps):
    def fake_get(url, params, timeout):
        if params["latitude"] == 0.0:
            return FakeResponse(404)
        return FakeResponse(200, {"hourly": {"time": ["2026-11-10T00:00"]}})

    monkeypatch.setattr("weatherflow.extract.requests.get", fake_get)
    config = {
        "api": API_CFG,
        "cities": [CITY, {"name": "Cardiff", "latitude": 0.0, "longitude": 0.0}],
        "paths": {"raw_dir": tmp_path},
    }
    results = extract(config)
    assert [name for name, _ in results] == ["London"]
    assert len(list(tmp_path.rglob("*.json"))) == 1