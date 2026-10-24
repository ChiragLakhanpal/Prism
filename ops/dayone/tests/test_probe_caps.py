"""The caps probe: each deployment's tokens-per-minute limit, the budget, and the subscription's offer.

Azure is replaced by a fake that returns what Azure Resource Manager returns for these calls.
"""

import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_caps  # noqa: E402
from dayone import Outcome, SetupError  # noqa: E402

from strata.config import load_models  # noqa: E402

# Each role's deployment, from the model file, so swapping a model there needs no change here.
NAME = {role: model.deployment for role, model in load_models().items()}


def deployment(name, sku, capacity, token_limit=None, state="Succeeded"):
    limits = [{"key": "request", "renewalPeriod": 10, "count": 1000}]
    if token_limit is not None:
        limits.append({"key": "token", "renewalPeriod": 60, "count": token_limit})
    return {"name": name, "sku": {"name": sku, "capacity": capacity},
            "properties": {"provisioningState": state, "rateLimits": limits}}


def notification(kind, threshold):
    return {"enabled": True, "operator": "GreaterThan", "threshold": threshold, "thresholdType": kind,
            "contactEmails": ["owner@example.org"]}


CAPPED = [
    deployment(NAME["agent"], "GlobalStandard", 100, 100000),
    deployment(NAME["draft"], "GlobalStandard", 30, 30000),
    deployment(NAME["batch"], "GlobalBatch", 2000),
    deployment(NAME["embed"], "GlobalStandard", 150),
]
BUDGET = {"name": "strata-monthly", "properties": {"amount": 50, "timeGrain": "Monthly", "notifications": {
    "actual_50": notification("Actual", 50), "actual_80": notification("Actual", 80),
    "actual_100": notification("Actual", 100), "forecast_100": notification("Forecasted", 100)}}}
FREE_TRIAL = {"displayName": "Azure subscription 1",
              "subscriptionPolicies": {"quotaId": "FreeTrial_2014-09-01", "spendingLimit": "On"}}
PAY_AS_YOU_GO = {"displayName": "Azure subscription 1",
                 "subscriptionPolicies": {"quotaId": "PayAsYouGo_2014-09-01", "spendingLimit": "Off"}}


class FakeAzure:
    def __init__(self, deployments=CAPPED, budgets=(BUDGET,), subscription=FREE_TRIAL, signed_out=False):
        self._deployments, self._budgets, self._subscription = deployments, list(budgets), subscription
        self.signed_out = signed_out

    def deployments(self):
        if self.signed_out:
            raise SetupError("az rest failed: Please run 'az login' to setup account.")
        return self._deployments

    def budgets(self):
        return self._budgets

    def subscription(self):
        return self._subscription


@pytest.fixture
def place(tmp_path):
    # A probe's first run starts from the template, whatever results the committed document holds.
    dayone.ensure_document(tmp_path / "results.md", dayone.load_config())
    shutil.copy(REPO / ".env.example", tmp_path / "probe.env")
    return tmp_path


def run(place, azure):
    return probe_caps.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                           service=azure)


def test_the_probe_prints_a_tokens_per_minute_limit_for_every_deployment(place, capsys):
    assert run(place, FakeAzure()) == 0
    shown = capsys.readouterr().out
    assert f"{NAME['agent']}: 100,000 tokens per minute" in shown
    assert f"{NAME['draft']}: 30,000 tokens per minute" in shown
    assert f"{NAME['embed']}: 150,000 tokens per minute" in shown
    batch = next(line for line in shown.splitlines() if f"{NAME['batch']}: " in line)
    assert "Global Batch" in batch and "2,000,000 enqueued tokens" in batch


def test_four_capped_deployments_pass_test_eight_and_the_caps_check(place):
    run(place, FakeAzure())
    results = dayone.read_results(place / "results.md")
    assert results["test-8"]["Status"] == "passed"
    assert results["caps"]["Status"] == "capped"
    assert len(results["caps"]["Deployments"]) == 4


def test_the_probe_checks_the_deployments_the_model_file_names(place, capsys):
    run(place, FakeAzure())
    shown = capsys.readouterr().out
    for model in load_models().values():
        assert f"    - {model.deployment}: " in shown


def test_a_model_swapped_in_the_model_file_is_the_one_the_probe_looks_for():
    models = load_models()
    models["agent"] = replace(models["agent"], deployment="swapped-model")

    outcome, _, _ = probe_caps.check(FakeAzure(), dayone.load_config(), models)

    assert outcome.status == "failed"
    assert "swapped-model: not found in wb-strata." in outcome.evidence


def test_the_passed_result_holds_for_however_many_deployments_dayone_toml_lists():
    config = dayone.load_config()
    del config["caps"]["deployments"]["embed"]
    outcome, _, _ = probe_caps.check(FakeAzure(deployments=CAPPED[:3]), config, load_models())
    assert outcome.status == "passed"
    assert outcome.result == "Every deployment with a cap in dayone.toml exists and finished deploying."


def test_a_missing_deployment_fails_test_eight(place):
    assert run(place, FakeAzure(deployments=CAPPED[:3])) == 1
    test8 = dayone.read_results(place / "results.md")["test-8"]
    assert test8["Status"] == "failed"
    assert any(NAME["embed"] in line and "not found" in line for line in test8["Evidence"])


def test_a_limit_above_its_cap_leaves_the_subscription_uncapped(place):
    loose = [deployment(NAME["draft"], "GlobalStandard", 300, 300000) if d["name"] == NAME["draft"] else d
             for d in CAPPED]
    assert run(place, FakeAzure(deployments=loose)) == 1
    caps = dayone.read_results(place / "results.md")["caps"]
    assert caps["Status"] == "not capped"
    assert any("300,000" in line and "30,000" in line for line in caps["Deployments"])


def test_a_batch_capacity_above_its_cap_leaves_the_subscription_uncapped(place):
    loose = [deployment(NAME["batch"], "GlobalBatch", 5000) if d["name"] == NAME["batch"] else d for d in CAPPED]
    assert run(place, FakeAzure(deployments=loose)) == 1
    caps = dayone.read_results(place / "results.md")["caps"]
    assert caps["Status"] == "not capped"
    assert any("5,000,000 enqueued tokens" in line and "2,000,000" in line for line in caps["Deployments"])


def test_a_budget_without_alerts_leaves_the_subscription_uncapped(place):
    quiet = {"name": "strata-monthly", "properties": {"amount": 50, "timeGrain": "Monthly", "notifications": {}}}
    assert run(place, FakeAzure(budgets=[quiet])) == 1
    caps = dayone.read_results(place / "results.md")["caps"]
    assert caps["Status"] == "not capped"
    assert "no alerts" in caps["Budget"]


def test_the_budget_line_counts_alerts_and_leaves_out_addresses(place):
    run(place, FakeAzure())
    caps = dayone.read_results(place / "results.md")["caps"]
    assert "US$50" in caps["Budget"] and "four alerts" in caps["Budget"]
    assert "sent to one email address" in caps["Budget"]
    assert "owner@example.org" not in (place / "results.md").read_text()


def test_a_pay_as_you_go_subscription_marks_the_step_done(place):
    run(place, FakeAzure(subscription=PAY_AS_YOU_GO))
    results = dayone.read_results(place / "results.md")
    assert "pay-as-you-go" in results["caps"]["Subscription offer"]
    assert results["payg"]["Status"].startswith("The subscription showed pay-as-you-go")


def test_a_free_trial_subscription_leaves_the_planned_step_alone(place):
    dayone.record_payg(place / "results.md", "planned", "The subscription owner", dayone.parse_day("2026-11-03"))
    run(place, FakeAzure(subscription=FREE_TRIAL))
    results = dayone.read_results(place / "results.md")
    assert "free trial" in results["caps"]["Subscription offer"]
    assert results["payg"]["Status"] == "Planned for November 3, 2026."


def test_a_dry_run_writes_nothing(place, capsys):
    before = (place / "results.md").read_text()
    assert probe_caps.main(["--dry-run", "--results", str(place / "results.md")]) == 0
    assert (place / "results.md").read_text() == before
    shown = capsys.readouterr().out
    assert "dry run" in shown
    assert f"{NAME['batch']}: 2,000,000 enqueued tokens" in shown


def test_an_az_that_cannot_read_keeps_the_wizards_test_8_record(place, capsys):
    wizard = Outcome("passed", "All four models deployed within the subscription's quota.", ["The person said so."])
    dayone.record_test(place / "results.md", 8, wizard)
    assert run(place, FakeAzure(signed_out=True)) != 0
    results = dayone.read_results(place / "results.md")
    assert results["test-8"]["Status"] == "passed"
    assert results["test-8"]["Evidence"] == ["The person said so."]
    assert results["caps"]["Status"] == "not checked"
    shown = capsys.readouterr().out
    assert "az login" in shown and "kept" in shown
