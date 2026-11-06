"""The demo seed for deep research: the items the sample brief cites, as one run dated November 5, 2026 (ticket 147).

    uv run python ops/research/seed.py --project P156634 --env-file .env       # on the workspace, as the app
    uv run python ops/research/seed.py --project P156634 --state-file state.duckdb   # in a local DuckDB file

It reads the sample's list of cited sources (ops/research/sample_<project>.toml, the 18 sources of the sample's last
page) and builds their items from the recordings, never from the network: the ISR passages and the notices from the
fixture database (data/out/fixture.duckdb, which the gate builds from the recorded documents and notices), the
Inspection Panel's register, the article pages and P513697's project record from data/fixture/recorded/research/,
and the Sentinel-2 grids from their addresses. Each of the seven sources is asked as a run asks it, so the run's
notes say what each answered that day: GDELT's 429 among them. The run is written through the research store
(src/strata/research/store.py), as the app's own service principal on the workspace, so the demo brief stands on the
App even when GDELT refuses that network. A second seed finds the run kept and changes nothing.

An article whose page answered a bot check (Eastleigh Voice's) keeps its headline as its text, the outlet's own
words, and the run's note for outlet_feeds names it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tomllib
from pathlib import Path

from strata.config import load_research
from strata.lakehouse.engine import DuckDBEngine
from strata.research import fetching
from strata.research.items import location_named, make_item, url_key
from strata.research.project import ProjectFacts, project_facts
from strata.research.sources import SourceResult, long_date, read
from strata.research.sources.outlet_feeds import _article
from strata.research.store import ResearchStore, Run

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded" / "research"
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
SEED_VIEWER = "prism"


def load_sample(project_id: str) -> dict:
    return tomllib.loads((HERE / f"sample_{project_id}.toml").read_text())


def _record_item(project: ProjectFacts, source, fetch, cited: dict, day: dt.date) -> dict:
    """A related project's record, from the projects API's recorded answer, in its own fields' words."""
    from strata.config import load_research_client

    url = load_research_client().project_record.format(project_id=cited["record"])
    record = json.loads(fetching.body_of(fetch, url, source.label))["projects"][cited["record"]]
    approved = (record.get("boardapprovaldate") or "")[:10] or None
    words = [f"{record['project_name']} ({record['id']}).", f"Board approval date: {approved}." if approved else "",
             f"Status: {record['status']}." if record.get("status") else "",
             f"Project development objective: {record['pdo']}" if record.get("pdo") else "",
             record.get("project_abstract") or ""]
    return make_item(project=project, source=source, item_key=f"record-{record['id']}", public_from=approved,
                     published=approved, title=f"World Bank project record: {record['project_name']} ({record['id']})",
                     text="\n\n".join(word for word in words if word), url=cited["url"], read_on=day,
                     author="World Bank", url_of_source=url)


def _article_item(project: ProjectFacts, source, fetch, cited: dict, day: dt.date) -> tuple[dict, str | None]:
    """An article the sample cites, from its recorded page; the headline stands in when the page refused."""
    text, printed, why = _article(fetch, cited["url"])
    published = printed or (dt.date.fromisoformat(cited["published"]) if cited.get("published") else None)
    feed = next((feed.url for feed in source.feeds if feed.outlet == cited["outlet"]), None)
    item = make_item(project=project, source=source, item_key=url_key(cited["url"]), public_from=published,
                     published=published, title=cited["title"], text=text or cited["title"], url=cited["url"],
                     read_on=day, author=cited["outlet"], location=location_named(project, cited["title"], text or ""),
                     url_of_source=feed)
    return item, (f"{cited['outlet']}'s page {why}" if why else None)


def sample_run(project_id: str, fixture: DuckDBEngine, recorded: Path = RECORDED) -> tuple[Run, list[dict]]:
    """The run and the items the sample cites, from the recordings and the fixture database."""
    sample = load_sample(project_id)
    day = sample["as_of"]
    now = dt.datetime.combine(day, dt.time(18), tzinfo=dt.UTC)
    sources = {key: source for key, source in load_research().items() if source.enabled}
    project = project_facts(project_id)
    fetch = fetching.offline(recorded)
    results: dict[str, SourceResult] = {key: read(source, project, fetch, fixture, now) for key, source in sources.items()}
    by_key = {item["evidence_id"].rsplit("/", 1)[-1]: item for result in results.values() for item in result.items}
    items, unread = [], []
    for cited in sample["cited"]:
        for entry in cited["items"]:
            source = sources[entry["source"]]
            if "key" in entry:
                found = by_key.get(entry["key"])
                if found is None:
                    raise LookupError(f"The {source.key} reader gave no item {entry['key']} for source "
                                      f"{cited['number']} of the sample.")
                items.append(found)
            elif "record" in entry:
                items.append(_record_item(project, source, fetch, entry, day))
            elif "url" in entry:
                item, why = _article_item(project, source, fetch, entry, day)
                items.append(item)
                if why:
                    unread.append(why)
    items = list({item["evidence_id"]: item for item in items}.values())
    counts = {key: sum(item["source"]["key"] == key for item in items) for key in sources}
    notes = {key: {"status": result.status, "note": result.note, "items": counts[key]} for key, result in results.items()}
    if unread:
        notes["outlet_feeds"]["note"] += (f" Of the pages the sample cites, {'; '.join(unread)}, so the headline "
                                          "stands in for the article.")
    started = dt.datetime.combine(day, dt.time(0), tzinfo=dt.UTC)
    run = Run(run_id=f"seed:{project_id}:{day.isoformat()}", project_id=project_id, started=started, as_of=day,
              sources_asked=tuple(sources), reached=tuple(key for key, result in results.items() if result.reached),
              finished=started, viewer=SEED_VIEWER,
              note=sample.get("note") or f"The items were read on {long_date(day)}.", source_notes=notes)
    return run, items


def seed(store: ResearchStore, project_id: str, fixture_db: Path = FIXTURE_DB, recorded: Path = RECORDED,
         say=print) -> bool:
    """Write the sample's run into the store; False when it is kept already."""
    with DuckDBEngine.open(fixture_db, read_only=True) as fixture:
        run, items = sample_run(project_id, fixture, recorded)
    if not store.save(run, items):
        say(f"The run {run.run_id} is kept already, so the seed changed nothing.")
        return False
    say(f"Kept the run {run.run_id} with {len(items)} items: " + ", ".join(
        f"{key} {note['items']}" for key, note in run.source_notes.items()) + ".")
    return True


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    import os

    from strata.seed_examples import read_env_file
    from strata.server.settings import _the_app_s_engine, app_state_file

    parser = argparse.ArgumentParser(description="Seed the sample deep research run for the demo.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file", help="the env file that names the workspace: write as the app on it")
    parser.add_argument("--state-file", help="a local DuckDB file to write instead, as scripts/dev's app state")
    arguments = parser.parse_args(argv)
    environ = dict(os.environ if environ is None else environ)
    if not FIXTURE_DB.is_file():
        print("Build the fixture database first: uv run --frozen python gates/build_fixture.py")
        return 1
    # The workspace as the app's own service principal, which the deploy grants research_runs and research_items
    # (ops/app/deploy_app.py; ops/app/tests/test_app_grants.py reads this function for the tables it writes).
    the_app = _the_app_s_engine(environ | read_env_file(arguments.env_file)) if arguments.env_file else None
    if arguments.env_file and the_app is None:
        print("I need the workspace: DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_CLIENT_ID and "
              "DATABRICKS_CLIENT_SECRET, in the env file --env-file names.")
        return 1
    path = arguments.state_file or environ.get("STRATA_APP_STATE_FILE", "")
    engine = the_app or (app_state_file({"STRATA_APP_STATE_FILE": path}) if path else None)
    if engine is None:
        print("Name where to write: --env-file for the workspace, or --state-file for a local DuckDB file.")
        return 1
    seed(ResearchStore(engine), arguments.project)
    return 0


if __name__ == "__main__":
    sys.exit(main())
