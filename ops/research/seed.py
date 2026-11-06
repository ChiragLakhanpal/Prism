"""The demo seed for deep research: the items each sample brief cites, as one run per project (tickets 147 and 152).

    uv run python ops/research/seed.py --project P156634 --env-file .env       # on the workspace, as the app
    uv run python ops/research/seed.py --project P156634 --project P161305 --env-file .env   # several projects
    uv run python ops/research/seed.py --all --env-file .env                    # every sample file present
    uv run python ops/research/seed.py --all --state-file state.duckdb           # in a local DuckDB file

It reads the sample's list of cited sources (ops/research/sample_<project>.toml, for P156634 the 18 sources of the
sample's last page) and builds their items without the network. The World Bank's own items, the ISR passages and the
procurement notices, come through the engine the store writes to (ticket 152): on the workspace from strata.gold.passage
and strata.gold.notice on the warehouse, so a project outside the fixture's documents gets them too; in a local
DuckDB file from the fixture database (data/out/fixture.duckdb, which the gate builds from the recorded documents and
notices). A notice the sample names by key is read by its id, whatever its date, so a closed project's notices load
too. The Inspection Panel's register, the article pages and the related projects' records come from
data/fixture/recorded/research/. The project's own record comes from the fixture's recorded page, else from the
projects API's answer recorded under data/fixture/recorded/research/ (with its locations, which bronze's copy may
lack), else from bronze. The Sentinel-2 grids come from their addresses: one grid for each location of the record and
for each of the sample's own sites, which its header may list as
sites = [{ name = "...", latitude = 0.0, longitude = 0.0 }, ...]. A site's grid has the item key
site-<n>-<first year>-<last year>, n counting from 1 in the header's order, unless the site gives its own geo_loc_id.
An item the sample cites that the seed cannot find is left out with a note in its source's line of the run and a line
on the screen, never a stop, and --all goes on to the next project when one fails. Each of the seven sources is asked as a run asks it, so the run's
notes say what each answered that day: GDELT's 429 among them. The run is written through the research store
(src/strata/research/store.py), as the app's own service principal on the workspace, so the demo brief stands on the
App even when GDELT refuses that network. A second seed finds the run kept and changes nothing.

Ticket 154's sources are asked too: GDACS's alerts, the agencies' own pages and the sanctions check, which reads a
downloaded copy of the World Bank's list under data/research/sanctions/ and the project's suppliers from the fixture
database. The run keeps every item these three readers give for the project (KEPT_WHOLE), beside the items the sample
lists, since they read the day's recordings of real, dated pages; the run's notes say what each answered, with the
items kept, and the sanctions check's note keeps its counts.

An article whose page answered a bot check (Eastleigh Voice's) keeps its headline as its text, the outlet's own
words, and the run's note for outlet_feeds names it.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

from strata.config import load_research
from strata.lakehouse.engine import DuckDBEngine, Engine, EngineError
from strata.research import fetching
from strata.research.items import location_named, make_item, url_key
from strata.research.project import Location, ProjectFacts, project_facts
from strata.research.sources import SourceResult, long_date, read
from strata.research.sources.outlet_feeds import _article
from strata.research.store import ResearchStore, Run

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded" / "research"
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
SAMPLES = HERE  # the sample files, sample_<project>.toml
SEED_VIEWER = "prism"
# The sources whose every item the seed keeps, not only those a sample lists (ticket 154): GDACS's alerts for the
# project's country, the agencies' own news pages, and the sanctions check's summary when the check ran.
KEPT_WHOLE = ("site_conditions", "agency_statements", "sanctions")


def load_sample(project_id: str, samples: Path | None = None) -> dict:
    return tomllib.loads(((samples or SAMPLES) / f"sample_{project_id}.toml").read_text())


def sample_projects(samples: Path | None = None) -> list[str]:
    """The projects with a sample file, in order."""
    return sorted(path.stem.removeprefix("sample_") for path in (samples or SAMPLES).glob("sample_P*.toml"))


def with_sites(project: ProjectFacts, sample: dict) -> ProjectFacts:
    """The project's facts with the sample's own sites after its record's locations, for the Sentinel-2 grids."""
    if not sample.get("sites"):
        return project
    sites = tuple(Location(str(site.get("geo_loc_id") or f"site-{number}"), site["name"], float(site["latitude"]),
                           float(site["longitude"])) for number, site in enumerate(sample["sites"], 1))
    return dataclasses.replace(project, locations=project.locations + sites)


def _facts(project_id: str, fetch, engine: Engine) -> ProjectFacts:
    """The project's record: the fixture's recorded page, the projects API's recorded answer (with its locations),
    or bronze through the engine."""
    try:
        return project_facts(project_id, fetch=fetch)
    except LookupError:
        try:
            return project_facts(project_id, engine=engine)
        except EngineError as error:
            raise LookupError(f"I found no recorded record of {project_id}, and bronze could not be read ({error}).") \
                from error


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


def _notice(source, project: ProjectFacts, bank: Engine, notice_id: str, day: dt.date) -> dict | None:
    """A notice the sample names by key, read by its id whatever its date; None when the table has no row."""
    from strata.research.sources import procurement_notices

    try:
        return procurement_notices.by_key(source, project, bank, notice_id, day)
    except EngineError:
        return None


def sample_run(project_id: str, bank: Engine, recorded: Path = RECORDED,
               samples: Path | None = None, say=print) -> tuple[Run, list[dict]]:
    """The run and the items the sample cites, from the recordings and the World Bank's records that bank reads (the
    warehouse's gold tables, or the fixture database)."""
    sample = load_sample(project_id, samples)
    day = sample["as_of"]
    now = dt.datetime.combine(day, dt.time(18), tzinfo=dt.UTC)
    sources = {key: source for key, source in load_research().items() if source.enabled}
    fetch = fetching.offline(recorded)
    project = _facts(project_id, fetch, bank)
    sited = with_sites(project, sample)  # the grids cover the sample's own sites too
    results: dict[str, SourceResult] = {
        key: read(source, sited if key == "sentinel2_mosaic" else project, fetch, bank, now)
        for key, source in sources.items()}
    by_key = {item["evidence_id"].rsplit("/", 1)[-1]: item for result in results.values() for item in result.items}
    items, unread, missing = [], [], {}
    for cited in sample["cited"]:
        for entry in cited["items"]:
            source = sources[entry["source"]]
            if "key" in entry:
                found = by_key.get(entry["key"])
                if found is None and source.key == "procurement_notices":
                    found = _notice(source, project, bank, entry["key"], day)
                if found is None:
                    missing.setdefault(source.key, []).append(entry["key"])
                    say(f"{project_id}: the {source.key} reader gave no item {entry['key']} for source "
                        f"{cited['number']} of the sample, so the run leaves it out.")
                    continue
                items.append(found)
            elif "record" in entry:
                items.append(_record_item(project, source, fetch, entry, day))
            elif "url" in entry:
                item, why = _article_item(project, source, fetch, entry, day)
                items.append(item)
                if why:
                    unread.append(why)
    # Ticket 154's readers answer from the recordings with real, dated pages, so the run keeps every item they give
    # for the project beside the sample's own, whether or not the sample lists it.
    items += [item for key in KEPT_WHOLE if key in results for item in results[key].items]
    items = list({item["evidence_id"]: item for item in items}.values())
    counts = {key: sum(item["source"]["key"] == key for item in items) for key in sources}
    notes = {key: {"status": result.status, "note": result.note, "items": counts[key], **result.counts}
             for key, result in results.items()}
    if unread:
        notes["outlet_feeds"]["note"] += (f" Of the pages the sample cites, {'; '.join(unread)}, so the headline "
                                          "stands in for the article.")
    for key, left in missing.items():
        notes[key]["note"] = (f"{notes[key]['note']} The sample cites {len(left)} more that this run could not find "
                              f"({', '.join(left)}), so they are left out.").strip()
    started = dt.datetime.combine(day, dt.time(0), tzinfo=dt.UTC)
    run = Run(run_id=f"seed:{project_id}:{day.isoformat()}", project_id=project_id, started=started, as_of=day,
              sources_asked=tuple(sources), reached=tuple(key for key, result in results.items() if result.reached),
              finished=started, viewer=SEED_VIEWER,
              note=sample.get("note") or f"The items were read on {long_date(day)}.", source_notes=notes)
    return run, items


def seed(store: ResearchStore, project_id: str, bank: Callable[[], Engine] | None = None, recorded: Path = RECORDED,
         samples: Path | None = None, say=print) -> bool:
    """Write the sample's run into the store; False when it is kept already. bank opens the engine the World Bank's
    own items are read through: the store's own unless it is given (the fixture database, for a local file)."""
    with fetching.opened(bank or store.engine) as engine:
        run, items = sample_run(project_id, engine, recorded, samples, say=say)
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

    arguments = _parser().parse_args(argv)
    environ = dict(os.environ if environ is None else environ)
    projects = projects_named(argv)
    if not projects:
        print("Name a project with --project, once for each project, or seed every sample file with --all.")
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
    # On the workspace the World Bank's items come through the store's own engine, the warehouse; a local file holds
    # no gold tables, so they come from the fixture database.
    bank = None
    if the_app is None:
        if not FIXTURE_DB.is_file():
            print("Build the fixture database first: uv run --frozen python gates/build_fixture.py")
            return 1
        fixture = FIXTURE_DB
        bank = lambda: DuckDBEngine.open(fixture, read_only=True)  # noqa: E731
    store = ResearchStore(engine)
    failed = []
    for project_id in projects:
        try:
            seed(store, project_id, bank=bank)
        except Exception as error:  # noqa: BLE001 - one project's failure leaves the others to seed
            failed.append(project_id)
            print(f"I could not seed {project_id}: {error}")
    if failed:
        print(f"Seeded {len(projects) - len(failed)} of {len(projects)} projects; not {', '.join(failed)}.")
    return 1 if failed else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed the sample deep research runs for the demo.")
    parser.add_argument("--project", action="append", default=[], help="a project with a sample file; repeat it")
    parser.add_argument("--all", action="store_true", help="every project with a sample file in ops/research")
    parser.add_argument("--env-file", help="the env file that names the workspace: write as the app on it")
    parser.add_argument("--state-file", help="a local DuckDB file to write instead, as scripts/dev's app state")
    return parser


def projects_named(argv: list[str], samples: Path | None = None) -> list[str]:
    """The projects the command line names: each --project, or every sample file's with --all."""
    arguments = _parser().parse_args(argv)
    return sample_projects(samples) if arguments.all else arguments.project


if __name__ == "__main__":
    sys.exit(main())
