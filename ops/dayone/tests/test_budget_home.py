"""The budget has one home, config/budget.toml (ticket 45): the wizard and the caps probe read it through dayone.py,
and the daily cost pull reads it through strata.config.load_budget, so the two never disagree."""

import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import dayone  # noqa: E402

ROOT = HERE.parents[2]


def budget_file() -> dict:
    return tomllib.loads((ROOT / "config" / "budget.toml").read_text())


def test_the_wizard_reads_the_credit_its_end_and_the_monthly_budget_from_the_budget_file():
    config, budget = dayone.load_config(), budget_file()

    assert config["payg"]["deadline"] == budget["credit"]["ends_on"].isoformat()
    assert config["payg"]["credit_usd"] == budget["credit"]["usd"]
    assert config["caps"]["monthly_budget_usd"] == budget["monthly"]["usd"]
    assert config["caps"]["budget_alert_percents"] == budget["monthly"]["alert_percents"]
    assert config["caps"]["budget_forecast_percent"] == budget["monthly"]["forecast_percent"]
    assert config["names"]["budget"] == budget["monthly"]["name"]
    assert config["names"]["resource_group"] == budget["pull"]["resource_group"]


def test_dayone_toml_no_longer_keeps_its_own_copy_of_the_budget():
    own = tomllib.loads((HERE.parent / "dayone.toml").read_text())

    assert "deadline" not in own["payg"] and "credit_usd" not in own["payg"]
    assert not {"monthly_budget_usd", "budget_alert_percents", "budget_forecast_percent"} & set(own["caps"])
    assert "budget" not in own["names"] and "resource_group" not in own["names"]
