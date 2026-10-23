"""The recording command. It refetches every source in data/fixture/sources.toml, prints a
diff against the recorded files, and overwrites them only when you pass --write.

    uv run python -m strata.fixture.record            # fetch and show what changed
    uv run python -m strata.fixture.record --write    # fetch and save the changes
    uv run python -m strata.fixture.record --only P130164 --write

It needs the network, so it is never a gate step. A file whose content did not change keeps
its Recorded date, so a refresh shows only real changes. Exit codes: 0 when nothing changed
or the changes were saved, 1 when there are changes you have not saved, 2 when a source
could not be fetched.
"""

import argparse
import difflib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from strata.fixture import recorded as fmt

USER_AGENT = "strata-fixture-recorder/0.1 (public World Bank open data)"
RETRIES = 4


def fetch_url(url):
    """GET a URL and return the body. Retries when the server asks us to wait or fails for a moment."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as failed:
            if failed.code not in (429, 500, 502, 503, 504) or attempt == RETRIES:
                raise
            body = failed.read().decode("utf-8", errors="replace")
            wait = re.search(r"again in (\d+) seconds", body)
            time.sleep(min(int(wait.group(1)) + 1, 90) if wait else 5 * attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == RETRIES:
                raise
            time.sleep(5 * attempt)
    raise RuntimeError(f"Could not fetch {url}")


def pdf_pages(pdf):
    """The text of each page of a PDF, read from its text layer."""
    from pypdf import PdfReader  # only the recording command needs it

    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages]


def fetched_files(source, fetch, today):
    """The recorded files for one source, as {relative path: bytes}, built from fresh fetches."""
    if source.kind == "json":
        response = json.loads(fetch(source.url))
        return {source.file: fmt.json_file(source.url, source.license, today, source.about, response)}
    text = fetch(source.text_url)
    pages = pdf_pages(fetch(source.pdf_url))
    header = {"License": source.license, "Recorded": today, "About": source.about}
    return {
        f"{source.file}.txt": fmt.text_file({"Source": source.text_url, **header}, text),
        f"{source.file}.pages.txt": fmt.text_file(
            {"Source": source.pdf_url, **header,
             "Pages": f"{len(pages)}, one after each form feed, read from the PDF's text layer"},
            fmt.PAGE_BREAK.join(pages).encode("utf-8")),
    }


def comparable(name, data):
    """The lines of a recorded file with its Recorded date left out, so a refetch on another day matches."""
    if data is None:
        return []
    if name.endswith(".json"):
        envelope = json.loads(data)
        envelope.pop("recorded", None)
        return json.dumps(envelope, indent=1, ensure_ascii=False).splitlines()
    head, _, body = data.partition(b"\n\n")
    kept = [line for line in head.decode("utf-8").splitlines() if not line.startswith("Recorded: ")]
    return kept + [""] + body.decode("utf-8", errors="replace").splitlines()


def show_diff(name, old, new, max_lines):
    lines = list(difflib.unified_diff(old, new, f"recorded/{name}", f"fetched/{name}", lineterm="", n=1))
    for line in lines[:max_lines]:
        print(line)
    if len(lines) > max_lines:
        print(f"... {len(lines) - max_lines} more diff lines. Pass --max-lines to see more.")


def parse(argv):
    parser = argparse.ArgumentParser(prog="python -m strata.fixture.record", description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="save the changes instead of only showing them")
    parser.add_argument("--only", action="append", default=[],
                        help="record only sources whose file contains this text (repeatable)")
    parser.add_argument("--manifest", default=str(fmt.MANIFEST), help="the list of sources")
    parser.add_argument("--max-lines", type=int, default=80, help="diff lines to print per file")
    return parser.parse_args(argv)


def main(argv=None, fetch=fetch_url):
    args = parse(argv)
    manifest = fmt.load_manifest(args.manifest)
    sources = [s for s in manifest.sources if not args.only or any(part in s.file for part in args.only)]
    today = date.today().isoformat()
    counts = {"new": 0, "changed": 0, "same": 0}
    failed = []
    print(f"Fetching {len(sources)} sources. Recorded files are in {manifest.recorded}.")
    for source in sources:
        try:
            files = fetched_files(source, fetch, today)
        except Exception as error:  # noqa: BLE001 - report every failure, then carry on
            failed.append(source.file)
            print(f"could not fetch  {source.file}: {type(error).__name__}: {error}")
            continue
        for name, data in files.items():
            path = manifest.recorded / name
            old = path.read_bytes() if path.exists() else None
            before, after = comparable(name, old), comparable(name, data)
            if before == after:
                counts["same"] += 1
                continue
            state = "new" if old is None else "changed"
            counts[state] += 1
            print(f"{state:<16} {name}")
            show_diff(name, before, after, args.max_lines)
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    pending = counts["new"] + counts["changed"]
    print(f"{counts['new']} new, {counts['changed']} changed and {counts['same']} the same; "
          f"{len(failed)} sources could not be fetched.")
    if failed:
        print("To try those again, run: uv run python -m strata.fixture.record "
              + " ".join(f"--only {name}" for name in failed) + (" --write" if args.write else ""))
        return 2
    if pending and not args.write:
        print("Nothing was saved. Run again with --write to save these changes.")
        return 1
    if pending:
        print(f"Saved {pending} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
