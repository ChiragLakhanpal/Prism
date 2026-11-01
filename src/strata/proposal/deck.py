"""The deck's data (ticket 47; the 47 brief, sections 6 and 9.1).

The deck at /present shows numbers from the same dated measures snapshot the proposal cites (snapshot.py), by the
same keys in the results register, so the two cannot disagree and the deck never waits for the warehouse in front of
the panel. build() gathers everything the slides read into one JSON object:

- results    each result the deck shows, its measured values and what the register says it is: its name, source
             kind, noun and table, which the number's tooltip and definition window print
- settings   each design count and planning choice the slides write as a word ("six checks", "two countries"),
             read from its registry through the settings register, as the proposal's Annex 2 reads it
- checks     the verifier's checks, in the order it runs them, which the checks slide counts
- rubric     the assessment's four dimensions and their points (config/rubric.toml, citing docs/assessment.md)
- urls       the panel's addresses (config/urls.toml); presenter, the title slide's name and date (config/deck.toml)
- designed_not_built  the parts designed but not built (config/designed_not_built.toml), for the last slide
- demo       the demo package and its plan (config/slice.toml [demo_plan]) and the answers find_comparables and
             estimate_time gave for it, recorded on the workspace (docs/proposal/demo-package.json); the package
             demo opens the live App, and its "Show the recorded answer" button draws the recorded comparables
             in its place when the App is down (ticket 116); for the second
             draft's demo slides, the plan's date, the Start here links they open
             (config/examples.toml, filled as Home fills them), the sentence the package demo types and the smoke
             question the answer demo asks (evals/benchmark.yaml)
- showcase   the showcase project (config/slice.toml [showcase]), whose disagreement the ladder slide quotes
- award_gap  the fiscal years no contract awards dataset publishes, from config/sources.toml's known gap, which the
             Data readiness page's Gap row shows; the rows-by-year series must agree with it

`uv run python -m strata.proposal deck` writes web/public/deck/data.json, which the built app serves and the deck
fetches. A result the snapshot has not measured is kept with "measured": false, and its slide says so.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from strata import config
from strata.proposal import register

ROOT = Path(__file__).resolve().parents[3]
DECK_FILE = ROOT / "web" / "public" / "deck" / "data.json"
DEMO_FILE = ROOT / "docs" / "proposal" / "demo-package.json"

# The results and settings the slides read, by their register keys.
RESULTS = ("passages", "documents-read", "pages-read-well", "award-rows-by-year", "linked-notice", "backtest-years",
           "award-rows-since-2020", "award-rows-2001-2016", "gap-contracts", "supplier-ids", "contacts-removed",
           "contacts-left", "disagreements",
           "benchmark-passed", "must-refuse", "hindsight-caught", "hindsight-checklist", "hindsight-interval",
           "azure-spend")
SETTINGS = ("check-count", "loop-count", "pilot-countries", "rollout-phases", "risks-per-package", "checklist-size",
            "hindsight-coders", "fewest-comparables")
DEMO_ANSWERS = ("comparables", "estimate")
# The known gap in config/sources.toml that the gap slide states: the fiscal years no contract awards dataset publishes.
AWARD_GAP = ("awards", "fy2017_2019")


class DeckError(ValueError):
    """Deck data the build cannot write, in a sentence that names the fix."""


def _results(snapshot: dict | None, keys: tuple[str, ...]) -> dict[str, dict]:
    defined = register.load_results()
    missing = [key for key in keys if key not in defined]
    if missing:
        raise DeckError(f"The deck reads {', '.join(missing)}, which docs/proposal/results.toml does not define. "
                        "Add the result there, with its query, or read one that is there.")
    measured = (snapshot or {}).get("results", {})
    return {key: {**(measured.get(key) or {"measured": False}), "name": defined[key].name, "kind": defined[key].kind,
                  "noun": defined[key].noun, "table": defined[key].table} for key in keys}


def _settings() -> dict[str, dict]:
    defined = register.load_settings()
    return {key: {"value": register.value(defined[key]).number, "name": defined[key].name,
                  "where": defined[key].where, "kind": "Count" if defined[key].read.startswith("count:") else "Setting"}
            for key in SETTINGS}


def _series_gap(series: list[dict]) -> dict | None:
    """The fiscal years after the first dataset's last year and before the last dataset's first, if there are any."""
    groups = list(dict.fromkeys(row["dataset"] for row in series))
    if len(groups) < 2:
        return None
    first_ends = max(row["fiscal_year"] for row in series if row["dataset"] == groups[0])
    last_starts = min(row["fiscal_year"] for row in series if row["dataset"] == groups[-1])
    return {"start": first_ends + 1, "end": last_starts - 1} if last_starts - first_ends > 1 else None


def _award_gap(result: dict) -> dict | None:
    """The known gap's fiscal years, from config/sources.toml, which the Data readiness page's Gap row shows too; the
    second draft states it whether or not the award rows are measured yet. Once they are, the rows-by-year series is a
    check: when it shows a different gap, the slide's sentence and its chart would disagree, so the build stops."""
    source, gap_id = AWARD_GAP
    known = next(gap for gap in config.load_sources()[source].known_gaps if gap.id == gap_id)
    gap = {"start": known.first_fiscal_year, "end": known.last_fiscal_year}
    if not result.get("measured"):
        return gap
    seen = _series_gap(result.get("series") or [])
    if seen is not None and seen != gap:
        raise DeckError(f"The award rows by year leave fiscal {seen['start']} to {seen['end']} empty, but "
                        f"config/sources.toml's known gap {gap_id} is fiscal {gap['start']} to {gap['end']}. "
                        "Check the snapshot's series, or correct the known gap.")
    return gap


def _smoke_question(key: str) -> str | None:
    """The words of the demo-ready command's smoke question (config/slice.toml [demo_plan] smoke_question), which the
    answer demo asks: the question in evals/benchmark.yaml with that id."""
    from strata.evals import benchmark

    return next((" ".join(question["question"].split()) for question in benchmark.load() if question.get("id") == key),
                None)


def _demo_links(agency: str, examples: config.Examples | None = None) -> dict:
    """The Start here links the demo slides open (config/examples.toml), filled as Home fills them, by key, and the
    sentence the package demo types into the box, the example its link names. The packages page reads that example
    from the link's query, so a link that names no example in the registry stops the build instead of leaving the
    package demo's box blank."""
    examples = examples or config.load_examples()
    links = {link["key"]: link["href"] for link in examples.links(agency)}
    sentence = None
    if "planPackage" in links:
        named = parse_qs(urlsplit(links["planPackage"]).query).get("example", [""])[0]
        if named not in examples.sentences:
            raise DeckError(f"config/examples.toml's planPackage link, {links['planPackage']}, names "
                            f"{f'the example {named}' if named else 'no example'}, but the package demo types the "
                            f"sentence of one of {', '.join(sorted(examples.sentences)) or 'no examples'}. Name one "
                            "of those in the link's example=, or add the example under [packages].")
        sentence = examples.sentences[named]
    return {"links": {key: links[key] for key in ("checkPlan", "planPackage", "wholeStory") if key in links},
            "sentence": sentence}


def _demo(answers: dict | None) -> dict:
    from strata.lakehouse.clean import agency_id

    plan = config.load_slice().demo_plan
    package = plan.package
    agency = agency_id(plan.implementing_agency)
    where = {"step_reference": package, "project_id": plan.project_id, "agency": plan.implementing_agency,
             "plan_date": plan.plan_date.isoformat(), "plan_href": f"/projects/{plan.project_id}/procurement/{agency}",
             **_demo_links(agency), "question": _smoke_question(plan.smoke_question)}
    if answers is None:
        return {**where, "comparables": None, "estimate": None}
    for name in DEMO_ANSWERS:
        found = ((answers.get(name) or {}).get("package") or {}).get("step_reference")
        if found != package:
            raise DeckError(f"The recorded {name} answer is for {found}, but config/slice.toml names {package} as "
                            "the demo package. Record both answers for the demo package again.")
    return {**where, **{name: answers[name] for name in DEMO_ANSWERS}}


def build(snapshot: dict | None, demo: dict | None, results: tuple[str, ...] = RESULTS) -> dict:
    """Everything the deck's slides read, from the snapshot (None before the first pull) and the demo's answers."""
    from strata.agent.verifier import ALL_CHECKS

    found = _results(snapshot, results)
    urls, rubric, presenter = config.load_urls(), config.load_rubric(), config.load_deck()
    return {
        "pulled_on": (snapshot or {}).get("pulled_on"),
        "results": found,
        "settings": _settings(),
        "checks": list(ALL_CHECKS),
        "rubric": {"source": rubric.source, "anchor": rubric.anchor,
                   "dimensions": [{"key": row.key, "name": row.name, "points": row.points}
                                  for row in rubric.dimensions]},
        "urls": {"app": urls.app, "dashboard": urls.dashboard, "repo": urls.repo, "deck": urls.deck,
                 "proposal": urls.proposal},
        "presenter": {"name": presenter.presenter_name,
                      "date": presenter.presentation_date.isoformat() if presenter.presentation_date else None},
        "designed_not_built": [{"key": item.key, "name": item.name, "route": item.route}
                               for item in config.load_designed_not_built()],
        "demo": _demo(demo),
        "showcase": {"project_id": config.load_slice().showcase.project_id},
        "award_gap": _award_gap(found["award-rows-by-year"]) if "award-rows-by-year" in found else None,
    }
