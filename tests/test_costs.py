"""Azure spend against the budget (ticket 45; the 45 brief, section 6.2, tiles 6 and 13 to 16).

The budget has one home, config/budget.toml, which strata.config.load_budget() reads: the free credit, the day it
ends, and the monthly budget after it. The daily cost pull (src/strata/lakehouse/costs.py) runs as its own bundle job
and asks Azure Cost Management for the resource group's charges. Offline, a recorded answer stands in for Azure
(tests/fixtures/azure_costs/query.json). Every pull writes a row to strata.ops.cost_pulls, its charges to
strata.ops.azure_costs, and the budget periods to strata.ops.budget_periods, which the Governance page reads.
"""

import datetime as dt
import json
from pathlib import Path

import pytest

from strata.config import load_budget
from strata.lakehouse import catalog, costs
from strata.lakehouse.engine import DuckDBEngine

FIXTURES = Path(__file__).parent / "fixtures" / "azure_costs"
PULLED_AT = dt.datetime(2026, 10, 23, 6, 0, tzinfo=dt.UTC)


@pytest.fixture
def ops(tmp_path):
    with DuckDBEngine.open(tmp_path / "ops.duckdb") as engine:
        catalog.build(engine)
        yield engine


def test_the_budget_file_holds_the_free_credit_its_end_and_the_monthly_budget():
    budget = load_budget()

    assert (budget.credit_usd, budget.credit_ends_on, budget.monthly_usd) == (197, dt.date(2026, 11, 10), 50)
    assert budget.name == "strata-monthly"


def test_the_budget_periods_are_the_free_credit_then_each_month_after_it_newest_first():
    periods = costs.periods(load_budget(), dt.date(2026, 12, 3))

    assert [(period.key, period.starts_on, period.ends_on, period.budget_usd) for period in periods] == [
        ("2026-12", dt.date(2026, 12, 1), dt.date(2026, 12, 31), 50),
        ("2026-11", dt.date(2026, 11, 11), dt.date(2026, 11, 30), 50),
        ("credit", None, dt.date(2026, 11, 10), 197)]
    assert [period.label for period in periods] == ["Dec 2026", "Nov 2026", "Free credit, to Nov 10, 2026"]


def test_before_the_credit_ends_the_only_period_is_the_free_credit():
    assert [period.key for period in costs.periods(load_budget(), dt.date(2026, 10, 23))] == ["credit"]


def recorded():
    return costs.RecordedCosts(json.loads((FIXTURES / "query.json").read_text()))


def test_a_pull_writes_each_day_s_charges_by_service_and_resource(ops):
    written = costs.pull(ops, recorded(), "pull-1", lambda: PULLED_AT)

    rows = ops.run("SELECT charged_on, service, resource, cost_usd FROM strata.ops.azure_costs "
                   "ORDER BY charged_on, service, resource").rows
    assert written == len(rows) == 6
    assert rows[0] == (dt.date(2026, 10, 20), "Application Insights", "wb-strata-insights", 0.1)
    assert rows[1] == (dt.date(2026, 10, 20), "Azure OpenAI", "wb-strata", 1.25)
    [pull] = ops.run("SELECT run_id, status, through_day, charges FROM strata.ops.cost_pulls").rows
    assert pull == ("pull-1", "succeeded", dt.date(2026, 10, 22), 6)


def test_a_pull_that_fails_is_recorded_with_why_and_writes_no_charges(ops):
    class Down:
        def charges(self, starts_on, ends_on):
            raise costs.CostError("not_authorized", "The service principal has no Cost Management Reader role.")

    with pytest.raises(costs.CostError):
        costs.pull(ops, Down(), "pull-2", lambda: PULLED_AT)

    assert ops.run("SELECT count(*) FROM strata.ops.azure_costs").rows == ((0,),)
    assert ops.run("SELECT run_id, status, error_code FROM strata.ops.cost_pulls").rows == (
        ("pull-2", "failed", "not_authorized"),)


def test_a_pull_writes_the_budget_periods_the_governance_page_offers(ops):
    costs.pull(ops, recorded(), "pull-1", lambda: PULLED_AT)

    assert ops.run("SELECT period_key, label, ends_on, budget_usd FROM strata.ops.budget_periods").rows == (
        ("credit", "Free credit, to Nov 10, 2026", dt.date(2026, 11, 10), 197.0),)


def test_the_live_adapter_signs_in_as_the_service_principal_and_reads_every_page_of_the_answer():
    """Azure Resource Manager's answer comes in pages linked by nextLink. The transport stands in for the network."""
    answer = json.loads((FIXTURES / "query.json").read_text())
    first = {"properties": {**answer["properties"], "rows": answer["properties"]["rows"][:4],
                            "nextLink": "https://management.azure.com/next-page"}}
    second = {"properties": {**answer["properties"], "rows": answer["properties"]["rows"][4:], "nextLink": None}}
    asked = []

    def transport(method, url, body, headers):
        asked.append((method, url.split("?")[0], headers.get("Authorization")))
        if "login.microsoftonline.com" in url:
            assert body["grant_type"] == "client_credentials" and body["scope"] == "https://management.azure.com/.default"
            return {"access_token": "not-a-real-key"}
        assert body["dataset"]["granularity"] == "Daily" and body["type"] == "ActualCost"
        return first if "next-page" not in url else second

    source = costs.AzureCostManagement("sub-id", "WorldBank-demo", "tenant-id", "client-id", "not-a-real-key",
                                       transport)
    found = source.charges(dt.date(2026, 9, 18), dt.date(2026, 10, 23))

    assert len(found) == 6 and found[-1].cost == 0.08
    assert asked[1] == ("POST", "https://management.azure.com/subscriptions/sub-id/resourceGroups/WorldBank-demo"
                                "/providers/Microsoft.CostManagement/query", "Bearer not-a-real-key")
    assert asked[2][1] == "https://management.azure.com/next-page"


def test_the_job_s_entry_point_records_a_failed_pull_when_the_secret_scope_lacks_a_key(ops):
    """cost_task.py reads the sign-in from the secret scope; with none there, the pull is recorded as failed and the
    Governance page's spend sentence says there is no cost data yet."""
    from strata.lakehouse import cost_task

    def secret(key):
        raise KeyError(key)

    with pytest.raises(costs.CostError):
        cost_task.main(["--run-id", "job-7"], ops, secret, lambda: PULLED_AT)

    assert ops.run("SELECT run_id, status, error_code FROM strata.ops.cost_pulls").rows == (
        ("job-7", "failed", "not_authorized"),)
    assert ops.run("SELECT section, finding FROM strata.ops.dashboard_findings").rows == ((
        "spend", "I have no Azure cost data yet. The daily cost pull adds each day's charges once Azure reports them."),)


def test_the_cost_pull_runs_as_its_own_daily_job_beside_the_nightly_one():
    """tests/test_nightly.py pins the nightly job's ten tasks, so the pull is a job of its own."""
    from strata.lakehouse import bundle

    job = bundle.load().resources("jobs")["costs"]
    [task] = job["tasks"]
    assert task["task_key"] == "pull_azure_costs"
    assert task["spark_python_task"]["python_file"].endswith("cost_task.py")
    assert job["schedule"]["quartz_cron_expression"].split()[3] == "*"  # every day
