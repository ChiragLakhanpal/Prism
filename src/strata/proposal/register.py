"""The proposal's two registers (ticket 46; the 46 brief, sections 9.3 and 9.4), and the change drill's rehearsal
record (ticket 49).

- The results register, docs/proposal/results.toml: each measured value the proposal cites, with the query that
  measures it. snapshot.pull() runs those queries; the build writes Annex 1 from this file and the snapshot.
- The settings register, docs/proposal/settings.toml: each value Strata is set to, or that counts a registry, with
  the file that sets it and the test that enforces it. settings() reads each value through strata.config's loaders,
  or from the caps Azure reported back (docs/day-one-results.md, written by ops/dayone/probe_caps.py), so a change
  drill changes the next build.
- The rehearsal record, docs/proposal/rehearsals.toml: how long each drill in config/change_drills.toml took when
  it was rehearsed. A rehearsal is measured on a branch, not queried from a table, so it has a file of its own
  beside the results register, and its source kind is "Rehearsal". The build writes each time into the change
  drill's table and its row into Annex 1.
"""

from __future__ import annotations

import datetime as dt
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / "docs" / "proposal"
RESULTS_FILE = FOLDER / "results.toml"
SETTINGS_FILE = FOLDER / "settings.toml"
REHEARSALS_FILE = FOLDER / "rehearsals.toml"
# The source kind of a rehearsal time, beside the 46 brief's six (section 9.2): a drill timed on its own branch.
REHEARSAL_KIND = "Rehearsal"
DRILL_BRANCH = "drill-49/"
DAY_ONE_FILE = ROOT / "docs" / "day-one-results.md"
DAY_ONE_CONFIG = ROOT / "ops" / "dayone" / "dayone.toml"

KINDS = ("Evaluation result", "Data readiness measure", "Benchmark run", "Backtest", "Hindsight test", "Query")
FORMS = ("ratio", "count", "money", "score", "days", "rate", "interval", "series", "fact", "text")
SETTING_FORMS = ("word", "number", "percent_band", "money", "tokens", "gigabytes")
READS = ("count", "threshold", "model", "cap", "plan")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
COUNTS = ("sources", "checks", "refusals", "ladder", "shelf", "drills", "loops")


class RegisterError(ValueError):
    """A register entry that does not follow its file's shape, in a sentence that names the fix."""


@dataclass(frozen=True)
class Result:
    """One measured value: what it counts, its source kind, and the query that measures it."""

    key: str
    name: str
    module: int
    kind: str
    noun: str
    query: str
    form: str
    table: str
    params: dict = field(default_factory=dict)
    meta: str | None = None
    row: dict | None = None
    columns: dict = field(default_factory=dict)
    count_of: str = "n"
    labels: str | None = None
    target: str | None = None

    @property
    def query_file(self) -> str:
        """The file Annex 1 links: a SQL file of the proposal's, or the dashboard query it reuses."""
        if self.query.startswith("dashboard:"):
            name = self.query.split(":", 1)[1]
            return (f"src/strata/dashboard/sql/kpi/{name[len('kpi_'):]}.sql" if name.startswith("kpi_")
                    else f"src/strata/dashboard/sql/{name}.sql")
        return f"src/strata/proposal/sql/{self.query}"


@dataclass(frozen=True)
class Setting:
    key: str
    name: str
    read: str
    form: str
    where: str
    second: str | None = None
    enforced_by: str | None = None
    enforces: str | None = None

    @property
    def planning_choice(self) -> bool:
        return self.read.startswith("plan:")


def _table(path: Path, name: str) -> dict:
    with open(path, "rb") as handle:
        data = tomllib.load(handle)
    if set(data) != {name} or not isinstance(data[name], dict):
        raise RegisterError(f"In {path.name}, write each entry as a [{name}.<key>] table, and nothing else.")
    return data[name]


def load_results(path: Path = RESULTS_FILE) -> dict[str, Result]:
    """Every result in the register, by key, in the file's order."""
    found = {}
    allowed = set(Result.__dataclass_fields__) - {"key"}
    for key, entry in _table(path, "results").items():
        unknown = sorted(set(entry) - allowed)
        if unknown:
            raise RegisterError(f"In {path.name}, results.{key} has keys I do not know: {', '.join(unknown)}.")
        if entry.get("kind") not in KINDS:
            raise RegisterError(f"In {path.name}, results.{key}.kind must be one of: {', '.join(KINDS)}.")
        if entry.get("form") not in FORMS:
            raise RegisterError(f"In {path.name}, results.{key}.form must be one of: {', '.join(FORMS)}.")
        if entry.get("module") not in (1, 2, 3, 4):
            raise RegisterError(f"In {path.name}, results.{key}.module must be 1, 2, 3 or 4.")
        missing = [name for name in ("name", "noun", "query", "table") if not entry.get(name)]
        if missing:
            raise RegisterError(f"In {path.name}, results.{key} needs {', '.join(missing)}.")
        found[key] = Result(key=key, **entry)
    return found


def load_settings(path: Path = SETTINGS_FILE) -> dict[str, Setting]:
    """Every setting in the register, by key, in the file's order."""
    found = {}
    allowed = set(Setting.__dataclass_fields__) - {"key"}
    for key, entry in _table(path, "settings").items():
        unknown = sorted(set(entry) - allowed)
        if unknown:
            raise RegisterError(f"In {path.name}, settings.{key} has keys I do not know: {', '.join(unknown)}.")
        if entry.get("read", "").split(":", 1)[0] not in READS:
            raise RegisterError(f"In {path.name}, settings.{key}.read must start with one of: "
                                f"{', '.join(read + ':' for read in READS)}.")
        if entry.get("form") not in SETTING_FORMS:
            raise RegisterError(f"In {path.name}, settings.{key}.form must be one of: {', '.join(SETTING_FORMS)}.")
        setting = Setting(key=key, **entry)
        if not setting.planning_choice and not setting.enforced_by:
            raise RegisterError(f"In {path.name}, settings.{key} needs enforced_by: the test that shows Strata keeps "
                                "it. Only a planning choice (plan:) has none.")
        found[key] = setting
    return found


# ── The rehearsal record ─────────────────────────────────────────────────

@dataclass(frozen=True)
class Rehearsal:
    """One drill of the change drill, timed: what it changed, on which branch and commit, and how long it took from
    making the branch to the commit the gate passed."""

    change: str
    example: str
    branch: str
    commit: str
    started_at: dt.datetime
    finished_at: dt.datetime
    gate_seconds: float

    @property
    def minutes(self) -> int:
        """Whole minutes, rounded up, so a drill never reads as shorter than it took."""
        return math.ceil((self.finished_at - self.started_at).total_seconds() / 60)

    @property
    def measured_on(self) -> dt.date:
        return self.finished_at.date()

    @property
    def key(self) -> str:
        """Its row's key in Annex 1, from its change: drill-add-a-data-source."""
        return "drill-" + re.sub(r"[^a-z0-9]+", "-", self.change.lower()).strip("-")


def load_rehearsals(path: Path = REHEARSALS_FILE) -> dict[str, Rehearsal]:
    """Every rehearsal in the record, by its change, in the file's order. Each names a drill of
    config/change_drills.toml word for word, once."""
    from strata.config import load_change_drills

    with open(path, "rb") as handle:
        data = tomllib.load(handle)
    if set(data) - {"rehearsals"}:
        raise RegisterError(f"In {path.name}, write each rehearsal as a [[rehearsals]] table, and nothing else.")
    changes = [drill.change for drill in load_change_drills()]
    found: dict[str, Rehearsal] = {}
    fields = set(Rehearsal.__dataclass_fields__)
    for number, entry in enumerate(data.get("rehearsals", []), 1):
        where = f"In {path.name}, rehearsal {number}"
        unknown, missing = sorted(set(entry) - fields), sorted(fields - set(entry))
        if unknown:
            raise RegisterError(f"{where} has keys I do not know: {', '.join(unknown)}.")
        if missing:
            raise RegisterError(f"{where} needs {', '.join(missing)}.")
        rehearsal = Rehearsal(**entry)
        if rehearsal.change not in changes:
            raise RegisterError(f"{where} times {rehearsal.change}, which config/change_drills.toml does not list. "
                                "Write the drill's change word for word.")
        if rehearsal.change in found:
            raise RegisterError(f"In {path.name}, {rehearsal.change} is rehearsed twice. Keep the run you mean.")
        if not all(isinstance(moment, dt.datetime) and moment.tzinfo for moment in (rehearsal.started_at,
                                                                                   rehearsal.finished_at)):
            raise RegisterError(f"{where}'s started_at and finished_at must be times with their offset, such as "
                                "2026-10-26T10:00:05-07:00.")
        if rehearsal.finished_at <= rehearsal.started_at:
            raise RegisterError(f"{where}'s finished_at must come after started_at.")
        if not rehearsal.branch.startswith(DRILL_BRANCH):
            raise RegisterError(f"{where}'s branch must start with {DRILL_BRANCH}, so nobody takes it for a ticket "
                                "branch and merges it.")
        if not re.fullmatch(r"[0-9a-f]{40}", rehearsal.commit):
            raise RegisterError(f"{where}'s commit must be the full 40-character hash the gate passed on.")
        if not isinstance(rehearsal.gate_seconds, int | float) or rehearsal.gate_seconds <= 0:
            raise RegisterError(f"{where}'s gate_seconds must be the gate's own time, a number of seconds above 0.")
        found[rehearsal.change] = rehearsal
    return found


# ── Setting values ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Value:
    """A setting's value as the proposal states it: the number, the text that shows it, and, for a cap, the day
    Azure reported it back, or why it was not."""

    number: float | int | None
    second: float | int | None = None
    read_back: dt.date | None = None
    not_read_back: str | None = None


def _count(name: str) -> int:
    from strata import config

    if name == "sources":
        return len(config.load_sources())
    if name == "checks":
        from strata.agent.verifier import ALL_CHECKS

        return len(ALL_CHECKS)
    if name == "refusals":
        from strata.agent.refusals import REFUSALS

        return len(REFUSALS)
    if name == "ladder":
        return len(config.load_ladder().rules)
    if name == "shelf":
        return len(config.load_slice().stress_shelf)
    if name == "drills":
        return len(config.load_change_drills())
    if name == "loops":
        return len({kpi.loop for kpi in config.load_kpis().values() if kpi.loop})
    raise RegisterError(f"count:{name} is not a registry I can count: use one of {', '.join(COUNTS)}.")


def read_back_caps(path: Path = DAY_ONE_FILE) -> tuple[dict[str, int], int | None, dt.date | None, str]:
    """The caps Azure reported back, from the dayone:caps block ops/dayone/probe_caps.py writes: each deployment's
    tokens by its name, the monthly budget in US dollars, the day they were checked, and the block's status."""
    text = path.read_text()
    block = re.search(r"<!-- dayone:caps -->(.*?)<!-- /dayone:caps -->", text, re.S)
    if not block:
        return {}, None, None, "missing"
    body = block.group(1)
    status = re.search(r"- Status: (.+)", body)
    tokens = {name: int(number.replace(",", ""))
              for name, number in re.findall(r"^\s+- ([\w.-]+): ([\d,]+) (?:tokens per minute|enqueued tokens)", body,
                                              re.M)}
    budget = re.search(r"- Budget: [^:]+: US\$([\d,]+) a month", body)
    checked = re.search(r"- Last checked: (\w+) (\d{1,2}), (\d{4})", body)
    day = (dt.date(int(checked.group(3)), MONTHS.index(checked.group(1)) + 1, int(checked.group(2)))
           if checked and checked.group(1) in MONTHS else None)
    return (tokens, int(budget.group(1).replace(",", "")) if budget else None, day,
            status.group(1).strip() if status else "missing")


def _cap(role: str, day_one: Path) -> Value:
    tokens, budget, checked, status = read_back_caps(day_one)
    if status != "capped" or checked is None:
        why = f"the probe's last status was \"{status}\""
    else:
        why = None
    if role == "budget":
        if budget is not None and why is None:
            return Value(budget, read_back=checked)
        from strata.config import load_budget

        return Value(load_budget().monthly_usd, not_read_back=why or "the probe found no budget")
    if role == "appinsights":
        with open(DAY_ONE_CONFIG, "rb") as handle:
            configured = tomllib.load(handle)["caps"]["appinsights_daily_cap_gb"]
        return Value(configured, not_read_back="the caps probe does not read Application Insights yet")
    from strata.config import load_models

    deployment = load_models()[role].deployment
    if deployment in tokens and why is None:
        return Value(tokens[deployment], read_back=checked)
    with open(DAY_ONE_CONFIG, "rb") as handle:
        cap = tomllib.load(handle)["caps"]["deployments"][role]
    return Value(cap.get("tokens_per_minute", cap.get("enqueued_tokens")),
                 not_read_back=why or f"the probe's block names no cap for {deployment}")


def value(setting: Setting, day_one: Path = DAY_ONE_FILE) -> Value:
    """A setting's value, read from the place that sets it."""
    kind, _, what = setting.read.partition(":")
    if kind == "count":
        return Value(_count(what))
    if kind == "threshold":
        from strata.config import load_thresholds

        thresholds = load_thresholds()
        return Value(thresholds.value(what), thresholds.value(setting.second) if setting.second else None)
    if kind == "model":
        from strata.config import load_models

        return Value(load_models()[what].dimensions)
    if kind == "cap":
        return _cap(what, day_one)
    if kind == "plan":
        return Value(int(what) if what.isdigit() else float(what))
    raise RegisterError(f"settings.{setting.key}.read is {setting.read}, which I can't read.")
