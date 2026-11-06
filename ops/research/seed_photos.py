"""The demo's field photos (ticket 156): openly licensed Wikimedia Commons photos taken near each seeded project's
sites, kept as field photos of the demo's World Bank staff team through the photo store of ticket 150, so the Deep
research tab and its print show a picture in every section.

    uv run python ops/research/seed_photos.py --all --env-file .env              # on the workspace, as the app
    uv run python ops/research/seed_photos.py --project P156634 --state-file state.duckdb   # in a local DuckDB file

The photos and their file pages' facts are recorded under data/fixture/field_photos/ (commons.json:
each photo's project, file, site, Commons title and page, author, license, the day it was taken and its position),
fetched with the named client prism-research/0.1 from Commons geosearch within 10 km of each site. No staff member
took them, so each caption says what it is: "Sample photo standing in for a staff photo: Wikimedia Commons, by
<author>, <license>, taken <date>." followed by the file's title. The brief cites a photo by that caption and its date,
never by its pixels.

On the workspace the files go into the strata.ops.field_photos volume and the rows into strata.ops.field_photos, as
the app's own service principal; in a local DuckDB file the files go in the folder beside it that the app reads. Each
photo is kept under the team config/roles.toml names first (the demo's staff team), or the one --team names, with the
sample's day as the day it was added, so a run as of that day cites it. A photo already kept is left as it is, so a
second seed changes nothing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from strata.research.photos import Photo, PhotoStore

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PHOTOS = ROOT / "data" / "fixture" / "field_photos"
UPLOADER_ID, UPLOADER_NAME = "prism-demo-seed", "Prism demo seed"
# The day the sample's items were read (ops/research/sample_<project>.toml's as_of), as the day each photo was added.
ADDED = dt.datetime(2026, 11, 5, 12, tzinfo=dt.UTC)


def _when(day: dt.date) -> str:
    return f"{day.strftime('%B')} {day.day}, {day.year}"


def recorded(folder: Path = PHOTOS) -> list[dict]:
    """The recorded photos, in the file's order."""
    return json.loads((folder / "commons.json").read_text())


def caption_of(entry: dict) -> str:
    """What the photo is, so nothing claims a World Bank staff member took it (the ticket's words), then its title."""
    title = entry["commons_title"].removeprefix("File:").rsplit(".", 1)[0].replace("_", " ")
    return (f"Sample photo standing in for a staff photo: Wikimedia Commons, by {entry['author']}, {entry['license']}, "
            f"taken {_when(dt.date.fromisoformat(entry['taken']))}. {title}.")


def photo_of(entry: dict, team_key: str) -> Photo:
    digest = hashlib.sha1(f"{entry['project']}/{entry['commons_title']}".encode()).hexdigest()[:12]
    photo_id = f"fph-{digest}"
    return Photo(photo_id, entry["project"], team_key, UPLOADER_ID, UPLOADER_NAME, entry["file"], caption_of(entry),
                 dt.date.fromisoformat(entry["taken"]), float(entry["latitude"]), float(entry["longitude"]),
                 entry["site"], None, f"{photo_id}.jpg", "image/jpeg", ADDED)


def seed(store: PhotoStore, projects: list[str], team_key: str, folder: Path = PHOTOS, say=print) -> dict[str, int]:
    """Keep each project's recorded photos under the team; the count kept now for each project."""
    counts = {project: 0 for project in projects}
    for entry in recorded(folder):
        if entry["project"] not in counts:
            continue
        photo = photo_of(entry, team_key)
        if store.get(photo.photo_id) is not None:
            say(f"{photo.project_id}: {entry['file']} is kept already as {photo.photo_id}.")
            continue
        store.create(photo, (folder / entry["file"]).read_bytes())
        counts[photo.project_id] += 1
        say(f"{photo.project_id}: kept {entry['file']} as {photo.photo_id}, near {photo.place}.")
    say("Field photos kept: " + ", ".join(f"{project} {count}" for project, count in counts.items()) + ".")
    return counts


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    import os

    from strata.config import load_field_photos, load_roles
    from strata.research.photos import LocalFiles
    from strata.seed_examples import read_env_file
    from strata.server.settings import _photo_files, _the_app_s_engine, app_state_file

    arguments = _parser().parse_args(argv)
    environ = dict(os.environ if environ is None else environ)
    known = sorted({entry["project"] for entry in recorded()})
    projects = known if arguments.all else arguments.project
    if not projects:
        print("Name a project with --project, once for each project, or seed every recorded photo with --all.")
        return 1
    teams = load_roles().teams
    team_key = f"team:{arguments.team or teams[0].key}"
    if arguments.env_file:
        env = environ | read_env_file(arguments.env_file)
        engine, files = _the_app_s_engine(env), _photo_files(env)
        if engine is None or files is None:
            print("I need the workspace: DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_CLIENT_ID and "
                  "DATABRICKS_CLIENT_SECRET, in the env file --env-file names.")
            return 1
    elif arguments.state_file:
        engine = app_state_file({"STRATA_APP_STATE_FILE": arguments.state_file})
        files = LocalFiles(Path(arguments.state_file).resolve().parent / load_field_photos().folder)
    else:
        print("Name where to write: --env-file for the workspace, or --state-file for a local DuckDB file.")
        return 1
    seed(PhotoStore(engine, files), projects, team_key)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed the demo's sample field photos for the staff team.")
    parser.add_argument("--project", action="append", default=[], help="a project with recorded photos; repeat it")
    parser.add_argument("--all", action="store_true", help="every project with recorded photos")
    parser.add_argument("--team", help="the team's key in config/roles.toml; the first team there by default")
    parser.add_argument("--env-file", help="the env file that names the workspace: write as the app on it")
    parser.add_argument("--state-file", help="a local DuckDB file to write instead, as scripts/dev's app state")
    return parser


if __name__ == "__main__":
    sys.exit(main())
