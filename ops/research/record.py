"""Record each deep research source's live answer for a project, so the offline tests and the demo seed read what
was public that day (ticket 147).

    uv run python ops/research/record.py --project P156634 --out data/fixture/recorded/research/
    uv run python ops/research/record.py --project P156634 --out data/fixture/recorded/research/ --sample
    uv run python ops/research/record.py --project P156634 --out data/fixture/recorded/research/ \
        --only site_conditions --country India --as-of 2026-11-05

It runs each enabled source that calls the network (config/research.toml) with the live fetch, Prism's named agent
and the source's pace, and writes every answer it got to <out>/<source>/<file>.json: the address, the status, the
date, the agent it was read with and the body (strata.research.fetching.recording). A host it could not reach is
recorded as unreachable, with the reason. The sentinel2_mosaic source fetches nothing, so the command probes one
tile of each year the registry lists, around the project's first location, and records the statuses without the
images. With --sample it also records the article pages and the project record the sample brief cites
(ops/research/sample_P156634.toml), under the source the seed gives them. It needs the network, so it is never a
gate step. --as-of reads as of that day, the day the seed and the tests read (the addresses that name a date then
match), and --country asks a source as the project would be asked in another country, with no approval date: the
site_conditions recording for India (ticket 154).
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
import tomllib
from pathlib import Path

from strata.config import load_research, load_research_client
from strata.research import fetching
from strata.research.project import project_facts
from strata.research.sources import read
from strata.research.sources.sentinel2_mosaic import grid

HERE = Path(__file__).resolve().parent
# An image a page inlines as a data: address, which no reader reads: NWWDA's article pages of November 5, 2026 inlined
# megabytes of them, so a recording keeps "data:," in their place.
INLINE_IMAGE = re.compile(rb"data:image/[\w.+-]+;base64,[A-Za-z0-9+/=\s]+")
NETWORK_SOURCES = ("gdelt_news", "outlet_feeds", "inspection_panel", "mastodon", "site_conditions",
                   "agency_statements")


def recorder(fetch: fetching.Fetch, folder: Path, source, today: dt.date, read_with: str,
             keep_body: bool = True) -> fetching.Fetch:
    """The fetch, writing each answer it gets into folder."""
    folder.mkdir(parents=True, exist_ok=True)

    def call(url: str, *, headers: dict | None = None) -> fetching.Answer:
        path = folder / fetching.recording_name(url)
        try:
            answer = fetch(url, headers=headers)
        except fetching.Unreachable as unreachable:
            entry = {"url": url, "source": source.key, "license": source.license, "recorded": today.isoformat(),
                     "read_with": read_with, "unreachable": unreachable.reason}
            path.write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n")
            print(f"  unreachable  {url}  ({unreachable.reason})")
            raise
        answer = (answer[0], answer[1], INLINE_IMAGE.sub(b"data:,", answer[2]))
        entry = fetching.recording(url, answer, source=source.key, license=source.license, recorded=today,
                                   read_with=read_with, keep_body=keep_body)
        path.write_text(json.dumps(entry, indent=1, ensure_ascii=False) + "\n")
        print(f"  {answer[0]}  {fetching.refusal(answer) or ''}  {url}")
        return answer

    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record each deep research source's live answer for a project.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only", help="the registry keys to record, comma separated")
    parser.add_argument("--sample", action="store_true", help="also record the sample brief's cited pages")
    parser.add_argument("--as-of", type=dt.date.fromisoformat, help="the day to read as of (the default is today)")
    parser.add_argument("--country", help="ask as the project would be asked in this country, with no approval date")
    arguments = parser.parse_args(argv)
    sources, client = load_research(), load_research_client()
    pacer, live, today = fetching.Pacer(), fetching.live(client), dt.date.today()
    now = dt.datetime.combine(arguments.as_of, dt.time(18), tzinfo=dt.UTC) if arguments.as_of else dt.datetime.now(dt.UTC)
    project = project_facts(arguments.project, fetch=live)
    if arguments.country:
        project = dataclasses.replace(project, country_name=arguments.country, approval_date=None)
    only = set(arguments.only.split(",")) if arguments.only else None
    for key in NETWORK_SOURCES:
        if only and key not in only:
            continue
        source = sources[key]
        print(f"{key}:")
        fetch = recorder(fetching.paced(live, key, source.pace_seconds, pacer), arguments.out / key, source, today,
                         client.user_agent)
        result = read(source, project, fetch, None, now)
        print(f"  reached {result.reached}, status {result.status}, {len(result.items)} items. {result.note}")
    if not only or "sentinel2_mosaic" in only:
        source = sources["sentinel2_mosaic"]
        print("sentinel2_mosaic (one tile a year, statuses only):")
        fetch = recorder(fetching.paced(live, source.key, 1, pacer), arguments.out / source.key, source, today,
                         client.user_agent, keep_body=False)
        first = next((place for place in project.locations if "Baricho" in place.name), project.locations[0])
        for year in range(2016, today.year + 1):
            try:
                fetch(grid(source.endpoint, year, first, int(source.settings.get("zoom", 15)))[4])
            except fetching.Unreachable:
                continue
    if arguments.sample:
        sample = tomllib.loads((HERE / f"sample_{arguments.project}.toml").read_text())
        print("the sample's cited pages:")
        for cited in sample["cited"]:
            for item in cited["items"]:
                if "url" not in item:
                    continue
                source = sources[item["source"]]
                folder = arguments.out / source.key
                fetch = recorder(fetching.paced(live, "sample", 2, pacer), folder, source, today, client.user_agent)
                url = (client.project_record.format(project_id=item["record"]) if item.get("record")
                       else item["url"])
                try:
                    fetch(url)
                except fetching.Unreachable:
                    continue
    return 0


if __name__ == "__main__":
    sys.exit(main())
