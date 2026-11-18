"""Tests for the command line and the config loader."""
from pathlib import Path

import pandas as pd
import pytest

from weatherflow import __main__ as cli
from weatherflow.config import CONFIG_FILE, load_config
from weatherflow.validate import DataQualityError


def test_run_command_calls_the_pipeline_and_returns_zero(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "load_config", lambda: {"marker": 1})
    monkeypatch.setattr(cli, "run", lambda config: calls.append(config))
    assert cli.main(["run"]) == 0
    assert calls == [{"marker": 1}]


def test_a_blocking_data_quality_failure_gives_exit_code_1(monkeypatch):
    def fail(config):
        raise DataQualityError("blocked", [], pd.DataFrame())

    monkeypatch.setattr(cli, "load_config", lambda: {})
    monkeypatch.setattr(cli, "run", fail)
    assert cli.main(["run"]) == 1


def test_an_unknown_command_exits_with_an_error():
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])


def test_paths_are_made_absolute_relative_to_the_config_file(tmp_path):
    copy = tmp_path / "config.yaml"
    copy.write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    config = load_config(copy)
    assert config["paths"]["database"] == (tmp_path / "data" / "weather.db").resolve()
    assert all(Path(p).is_absolute() for p in config["paths"].values())


def test_a_missing_section_gives_a_clear_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("paths: {}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="api"):
        load_config(path)


def test_an_empty_config_file_is_rejected(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_config(path)