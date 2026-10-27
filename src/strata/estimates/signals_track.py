"""The signals' track record (ticket 37): the replay harness's signals_track_record scorer, and the stored results
the Following page reads.

The scorer replays project_signals as it would have run on each of the thresholds file's
signals.track_record_dates, on every project whose loan history was public by then and still open, each through
a reader frozen at that date (src/strata/estimates/harness.py), so no record published later reaches it. It then
reads what happened next at the outcomes date: whether the loan history shows the project's closing date moved
later within signals.track_record_window_months after a date. For each status (Needs a look, Watch, No signals)
and each check, it counts the projects that had it on at least one replay date (n) and those of them whose
closing date then moved later (k). A project that could not be checked, or had closed, is not counted.

The harness appends the counts to strata.ops.evaluation_result under one segment, segment_kind "replay", with the
replay dates, the window and the cohort's size, and logs them to MLflow. stored() reads the latest run, and says
which counts are too few to read as a rate (signals.track_record_min), so the page states only stored numbers and
never counts anything itself. With no run stored, it returns None, and the page says the checks were never
replayed.

On the workspace, the nightly job's score task runs backtest() once a week, on the night signals.track_record_day
names (tickets 43 and 89); ops/signals/replay_live.py runs it by hand.
"""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict

from strata.config import Thresholds, load_thresholds
from strata.estimates import harness
from strata.estimates.harness import Reader, Replay, Score, Scored, Window
from strata.estimates.past_range import as_date
from strata.tools.project_signals import ACTIVE, CHECKS, months_after
from strata.tools.withheld import statuses_between

SCORER = "signals_track_record"
MODEL = "strata.tools.project_signals"
SEGMENT_KIND, SEGMENT = "replay", "signals"
STATUSES = ("needs_a_look", "watch", "no_signals")

# Every project whose monthly loan history was public by the reader's date: the cohort the checks are replayed on.
COHORT = """
SELECT project_id, max(public_from) AS public_from
FROM strata.gold.project_closing_date
WHERE public_from <= :as_of
GROUP BY project_id
ORDER BY project_id
"""

# Each month the loan history showed a project's closing date moved later, as public by the outcomes date.
MOVES = """
SELECT project_id, reported_on, public_from
FROM strata.gold.project_closing_date
WHERE public_from <= :as_of
  AND previous_closing_date IS NOT NULL
  AND closing_date > previous_closing_date
ORDER BY project_id, reported_on
"""


# What counted() found on each replay date, kept by the caller for the replays of one night, which read the same
# engine with the same thresholds.
Checked = dict[dt.date, list[tuple[str, dict]]]


def counted(frozen: Reader, checked: Checked | None = None) -> list[tuple[str, dict]]:
    """Each project of the cohort on the reader's date that the track record counts, with project_signals' result:
    a project the checks gave a status (STATUSES). The cohort is read signals.track_record_batch_projects projects
    at a time, with two statements for each batch (strata.tools.withheld.statuses_between), and only a project
    still active on the date is checked, since project_signals counts no other: it answers not_active for a closed,
    pipeline or dropped project and no_records for one with no record. Checked one at a time, each of the cohort's
    projects cost the SQL warehouse two statements on each date, about 110 minutes in all on the paid workspace's
    cohort (ticket 89). With checked, a date already in it is read from there, and a date read is kept there, so the
    track record and the hazard model's comparison, which replay the same dates, check each project once a date."""
    if checked is not None and frozen.as_of in checked:
        return checked[frozen.as_of]
    cohort = [row["project_id"] for row in frozen.rows(COHORT)]
    size = int(frozen.thresholds.value("signals.track_record_batch_projects"))
    found = []
    for start in range(0, len(cohort), size):
        batch = cohort[start:start + size]
        statuses = statuses_between(frozen.rows, batch[0], batch[-1], frozen.as_of)
        for project_id in batch:
            if statuses.get(project_id) != ACTIVE:
                continue
            result = frozen.call("project_signals", project_id=project_id)
            if result["status"] in STATUSES:
                found.append((project_id, result))
    if checked is not None:
        checked[frozen.as_of] = found
    return found


def later_moves(outcomes: Reader) -> defaultdict[str, list[dt.date]]:
    """For each project, the months the loan history showed its closing date moved later, as public by the outcomes
    reader's date, read with one statement for every project."""
    moves: defaultdict[str, list[dt.date]] = defaultdict(list)
    for row in outcomes.rows(MOVES):
        moves[row["project_id"]].append(as_date(row["reported_on"]))
    return moves


class SignalsTrackRecord:
    name = SCORER
    model = MODEL

    def __init__(self, dates: tuple[dt.date, ...], window_months: int, checked: Checked | None = None):
        self.dates, self.window_months, self.checked = dates, window_months, checked

    def score(self, replay: Replay) -> Scored:
        had: dict[str, set[str]] = {key: set() for key in (*STATUSES, *CHECKS)}
        moved: dict[str, set[str]] = {key: set() for key in had}
        cohort: set[str] = set()
        moves = later_moves(replay.outcomes)
        for date in (day for day in self.dates if day <= replay.window.cutoff):
            frozen = Reader(replay.inputs.engine, date, replay.thresholds)
            later = months_after(date, self.window_months)
            for pid, result in counted(frozen, self.checked):
                cohort.add(pid)
                extended = any(date < moved_on <= later for moved_on in moves[pid])
                for key in (result["status"], *(row["check"] for row in result["rows"])):
                    had[key].add(pid)
                    if extended:
                        moved[key].add(pid)
        scores = [Score(f"{'status' if key in STATUSES else 'check'}.{key}.{measure}", len(found[key]))
                  for key in had for measure, found in (("n", had), ("k", moved))]
        scores += [Score("dates", text=json.dumps([day.isoformat() for day in self.dates if day <= replay.window.cutoff])),
                   Score("window_months", self.window_months), Score("cohort", len(cohort))]
        return Scored(scores, {"dates": len(self.dates), "window_months": self.window_months})


def settings(thresholds: Thresholds) -> tuple[tuple[dt.date, ...], int]:
    dates = tuple(sorted(as_date(day) for day in thresholds.value("signals.track_record_dates")))
    return dates, int(thresholds.value("signals.track_record_window_months"))


def backtest(engine, tracker, *, store=None, thresholds: Thresholds | None = None, ran_at: dt.datetime | None = None,
             outcomes_through: dt.date | None = None, checked: Checked | None = None) -> str:
    """Replay the checks on every track record date, store the counts and return the run's id. The outcomes are read
    as of the last date plus the window, or the day it runs when that is earlier. checked is what the night's other
    replay found on each date, if any (counted)."""
    thresholds = thresholds or load_thresholds()
    ran_at = ran_at or dt.datetime.now(dt.UTC)
    dates, window = settings(thresholds)
    through = outcomes_through or min(months_after(dates[-1], window), ran_at.date())
    run_id = harness.new_run_id(SCORER, ran_at)
    harness.replay(engine, SignalsTrackRecord(dates, window, checked),
                   Window(dates[-1], through, SEGMENT_KIND, SEGMENT), tracker, run_id, ran_at, store or engine,
                   thresholds)
    return run_id


def stored(engine, thresholds: Thresholds | None = None) -> dict | None:
    """The latest stored track record, in the page's shape, or None when the checks were never replayed."""
    thresholds = thresholds or load_thresholds()
    run_id = harness.latest_run(engine, SCORER)
    if run_id is None:
        return None
    record = harness.segments(harness.run_rows(engine, run_id)).get((SEGMENT_KIND, SEGMENT))
    if record is None:
        return None
    least = int(thresholds.value("signals.track_record_min"))

    def counts(kind: str, key: str) -> dict:
        n, k = record.get(f"{kind}.{key}.n"), record.get(f"{kind}.{key}.k")
        return {"n": n, "k": k, "few": n is not None and n < least}

    ran_at = record["ran_at"]
    ran_on = ran_at.date() if isinstance(ran_at, dt.datetime) else as_date(ran_at)
    return {"run_id": run_id, "mlflow_run_id": record["mlflow_run_id"], "ran_on": ran_on.isoformat(),
            "dates": json.loads(record["dates"]), "window_months": record["window_months"], "cohort": record["cohort"],
            "outcomes_through": record["outcomes_through"].isoformat() if record["outcomes_through"] else None,
            "min": least, "status": {key: counts("status", key) for key in STATUSES},
            "checks": {key: counts("check", key) for key in CHECKS}}
