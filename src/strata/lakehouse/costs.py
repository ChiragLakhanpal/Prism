"""The daily cost pull: Azure's charges for Strata's resource group, into strata.ops (ticket 45).

The Governance page shows Azure spend against the budget (the 45 brief, section 6.2, tiles 6 and 13 to 16; spec
story 121). Azure budgets only send email, so the dashboard reads the charges themselves. The pull runs as its own
bundle job, bundle/costs.yml, once a day after the nightly job, because tests/test_nightly.py keeps the nightly job
to PLAN.md section 11's ten tasks.

Each pull asks Azure Cost Management for the last pull_days days of the resource group's actual cost, by day,
service and resource (config/budget.toml), and appends:

- its charges to strata.ops.azure_costs, under its run id. Azure revises recent days, so a reader takes each day from
  the newest pull that holds it;
- one row to strata.ops.cost_pulls, succeeded or failed, with the last day Azure gave charges for, or why it stopped;
- the budget periods to strata.ops.budget_periods: the free credit up to the day it ends, then each month after it,
  newest first, with the words the Budget period filter shows (copy.dash.periods).

Two adapters stand behind CostSource: AzureCostManagement calls Azure Resource Manager with a service principal's
token, on the workspace; RecordedCosts reads an answer of the same shape from a file, offline
(tests/fixtures/azure_costs/query.json, made up for the tests, since no live answer may enter the repo).
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from strata.config import Budget, load_budget
from strata.dashboard import wording as dash_words
from strata.lakehouse.engine import Engine

COSTS = "strata.ops.azure_costs"
PULLS = "strata.ops.cost_pulls"
PERIODS = "strata.ops.budget_periods"
COST_COLUMNS = ("run_id", "charged_on", "service", "resource", "cost_usd", "currency", "pulled_at", "public_from")
PULL_COLUMNS = ("run_id", "pulled_at", "status", "from_day", "through_day", "charges", "error_code", "public_from")
PERIOD_COLUMNS = ("run_id", "position", "period_key", "label", "name", "starts_on", "ends_on", "budget_usd",
                  "written_at", "public_from")
ERROR_CODES = ("not_authorized", "throttled", "bad_answer", "unreachable")
API_VERSION = "2023-11-01"


class CostError(Exception):
    """A pull that could not read Azure's charges, with a code from ERROR_CODES."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code if code in ERROR_CODES else "bad_answer"


@dataclass(frozen=True)
class Charge:
    charged_on: dt.date
    service: str
    resource: str
    cost: float
    currency: str


class CostSource(Protocol):
    def charges(self, starts_on: dt.date, ends_on: dt.date) -> list[Charge]: ...


def _resource_name(resource_id: str) -> str:
    return resource_id.rstrip("/").rsplit("/", 1)[-1] if resource_id else ""


def parse(answer: dict) -> list[Charge]:
    """The charges in one page of Azure Cost Management's query answer, found by column name."""
    try:
        properties = answer["properties"]
        names = [column["name"] for column in properties["columns"]]
        cost = names.index("Cost") if "Cost" in names else names.index("PreTaxCost")
        day, service = names.index("UsageDate"), names.index("ServiceName")
        resource, currency = names.index("ResourceId"), names.index("Currency")
        found = []
        for row in properties["rows"]:
            charged = str(int(row[day]))
            found.append(Charge(dt.date(int(charged[:4]), int(charged[4:6]), int(charged[6:])), str(row[service]),
                                _resource_name(str(row[resource])), float(row[cost]), str(row[currency])))
        return found
    except (KeyError, ValueError, TypeError, IndexError) as error:
        raise CostError("bad_answer", f"Azure's cost answer was not in the shape I read: {error}") from error


class RecordedCosts:
    """A recorded answer, for the offline gate: its charges between the days asked for."""

    def __init__(self, answer: dict):
        self.answer = answer

    def charges(self, starts_on: dt.date, ends_on: dt.date) -> list[Charge]:
        return [charge for charge in parse(self.answer) if starts_on <= charge.charged_on <= ends_on]


Transport = Callable[[str, str, dict | None, dict], dict]


def _http(method: str, url: str, body: dict | None, headers: dict) -> dict:
    data = (json.dumps(body).encode() if headers.get("Content-Type") == "application/json"
            else urllib.parse.urlencode(body).encode()) if body is not None else None
    request = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        code = "not_authorized" if error.code in (401, 403) else "throttled" if error.code == 429 else "bad_answer"
        raise CostError(code, f"Azure answered {error.code}: {error.read().decode(errors='replace')[:300]}") from error
    except OSError as error:
        raise CostError("unreachable", f"I could not reach Azure: {error}") from error


class AzureCostManagement:
    """Azure Cost Management's query API for one resource group, with a service principal's token. The token stays
    inside this object and never reaches a log or a table."""

    def __init__(self, subscription_id: str, resource_group: str, tenant_id: str, client_id: str, credential: str,
                 transport: Transport = _http):
        self.scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        self.tenant_id, self.client_id, self._credential = tenant_id, client_id, credential
        self.transport = transport

    def _token(self) -> str:
        answer = self.transport("POST", f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token", {
            "grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self._credential,
            "scope": "https://management.azure.com/.default"}, {"Content-Type": "application/x-www-form-urlencoded"})
        if not answer.get("access_token"):
            raise CostError("not_authorized", "Microsoft Entra ID gave no token for the service principal.")
        return answer["access_token"]

    def charges(self, starts_on: dt.date, ends_on: dt.date) -> list[Charge]:
        headers = {"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"}
        body = {"type": "ActualCost", "timeframe": "Custom",
                "timePeriod": {"from": f"{starts_on.isoformat()}T00:00:00Z", "to": f"{ends_on.isoformat()}T23:59:59Z"},
                "dataset": {"granularity": "Daily",
                            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                            "grouping": [{"type": "Dimension", "name": "ServiceName"},
                                         {"type": "Dimension", "name": "ResourceId"}]}}
        url = (f"https://management.azure.com{self.scope}/providers/Microsoft.CostManagement/query"
               f"?api-version={API_VERSION}")
        found: list[Charge] = []
        while url:
            answer = self.transport("POST", url, body, headers)
            found += parse(answer)
            url = (answer.get("properties") or {}).get("nextLink")
        return found


# ── Budget periods ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Period:
    key: str
    starts_on: dt.date | None
    ends_on: dt.date
    budget_usd: int
    label: str
    name: str


def _month_end(day: dt.date) -> dt.date:
    following = day.replace(day=28) + dt.timedelta(days=4)
    return following - dt.timedelta(days=following.day)


def periods(budget: Budget, today: dt.date) -> list[Period]:
    """The budget periods up to today, newest first: each month after the credit ends, then the free credit."""
    say = dash_words.at("dash.periods")
    ends = budget.credit_ends_on
    found = [Period("credit", None, ends, budget.credit_usd,
                    dash_words.fill(say["credit"], date=dash_words.table_day(ends)),
                    dash_words.fill(say["creditName"], phrase=True, date=dash_words.long_day(ends)))]
    start = ends + dt.timedelta(days=1)
    while start <= today:
        end = _month_end(start)
        found.append(Period(start.strftime("%Y-%m"), start, end, budget.monthly_usd, dash_words.short_month(start),
                            dash_words.month_name(start)))
        start = end + dt.timedelta(days=1)
    return found[::-1]


def current_period(budget: Budget, today: dt.date) -> Period:
    """The period today falls in: the dashboard's Budget period filter starts at it."""
    return periods(budget, today)[0]


# ── The pull ─────────────────────────────────────────────────────────────

def pull(engine: Engine, source: CostSource, run_id: str, clock: Callable[[], dt.datetime],
         budget: Budget | None = None) -> int:
    """Read the last pull_days days of charges and write them, the pull's row and the budget periods. Returns how
    many charges it wrote. A pull that fails writes its row with why, and raises again."""
    budget = budget or load_budget()
    pulled_at = clock()
    today = pulled_at.astimezone(dt.UTC).date()
    starts_on = today - dt.timedelta(days=budget.pull_days)
    try:
        found = source.charges(starts_on, today)
    except Exception as error:
        code = error.code if isinstance(error, CostError) else "bad_answer"
        engine.insert_rows(PULLS, PULL_COLUMNS, [(run_id, pulled_at, "failed", starts_on, None, 0, code, today)])
        raise
    engine.insert_rows(COSTS, COST_COLUMNS, [
        (run_id, charge.charged_on, charge.service, charge.resource, round(charge.cost, 6), charge.currency, pulled_at,
         today) for charge in found])
    through = max((charge.charged_on for charge in found), default=None)
    engine.insert_rows(PULLS, PULL_COLUMNS, [(run_id, pulled_at, "succeeded", starts_on, through, len(found), None,
                                              today)])
    engine.insert_rows(PERIODS, PERIOD_COLUMNS, [
        (run_id, position, period.key, period.label, period.name, period.starts_on, period.ends_on,
         float(period.budget_usd), pulled_at, today) for position, period in enumerate(periods(budget, today), 1)])
    return len(found)
