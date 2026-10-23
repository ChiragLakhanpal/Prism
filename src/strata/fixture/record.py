"""The recording command. It refetches every source in data/fixture/sources.toml, prints a
diff against the recorded files, and overwrites them only when you pass --write.

    uv run python -m strata.fixture.record            # fetch and show what changed
    uv run python -m strata.fixture.record --write    # fetch and save the changes
    uv run python -m strata.fixture.record --only P130164 --write

It needs the network, so it is never a gate step. A file whose content did not change keeps
its Recorded date, so a refresh shows only real changes. The diff leaves out each dataset's
ignore_keys, such as the as_of_date that Finances One stamps on each row every day. Exit codes: 0 when nothing changed
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


def count(n, word):
    """"1 source" or "2 sources"."""
    return f"{n} {word}{'' if n == 1 else 's'}"


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


WORDS_READ_WITH = ("poppler's pdftotext -bbox: each word is \"x0 y0 x1 y1 text\", in points from the page's "
                   "top left")


def pdf_words(pdf):
    """The words on each page of a PDF with their boxes, read with poppler's pdftotext -bbox.

    Each page is {"width", "height", "words"}, and each word is (x0, y0, x1, y1, text). The
    recording command needs pdftotext installed (Homebrew: brew install poppler).
    """
    import html
    import shutil
    import subprocess
    import tempfile

    if shutil.which("pdftotext") is None:
        raise RuntimeError("Recording a document's words needs poppler's pdftotext. Install poppler, "
                           "for example with: brew install poppler")
    with tempfile.TemporaryDirectory() as folder:
        path = f"{folder}/document.pdf"
        with open(path, "wb") as handle:
            handle.write(pdf)
        out = subprocess.run(["pdftotext", "-bbox", path, "-"], capture_output=True, check=True).stdout
    pages = []
    for width, height, body in re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>',
                                          out.decode("utf-8"), re.S):
        words = [(float(x0), float(y0), float(x1), float(y1), html.unescape(text)) for x0, y0, x1, y1, text in
                 re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',
                            body)]
        pages.append({"width": float(width), "height": float(height), "words": words})
    return pages


def words_response(pages):
    """The response a words file keeps: each word as one line of text, so a refresh diffs word by word."""
    return {"read_with": WORDS_READ_WITH,
            "pages": [{"width": page["width"], "height": page["height"],
                       "words": [f"{round(x0, 2):g} {round(y0, 2):g} {round(x1, 2):g} {round(y1, 2):g} {text}"
                                 for x0, y0, x1, y1, text in page["words"]]}
                      for page in pages]}


def fetched_files(source, fetch, today, words=pdf_words):
    """The recorded files for one source, as {relative path: bytes}, built from fresh fetches."""
    if source.kind == "json":
        response = json.loads(fetch(source.url))
        return {source.file: fmt.json_file(source.url, source.license, today, source.about, response)}
    text = fetch(source.text_url)
    pdf = fetch(source.pdf_url)
    pages = pdf_pages(pdf)
    header = {"License": source.license, "Recorded": today, "About": source.about}
    files = {
        f"{source.file}.txt": fmt.text_file({"Source": source.text_url, **header}, text),
        f"{source.file}.pages.txt": fmt.text_file(
            {"Source": source.pdf_url, **header,
             "Pages": f"{len(pages)}, one after each form feed, read from the PDF's text layer"},
            fmt.PAGE_BREAK.join(pages).encode("utf-8")),
    }
    if source.words:
        files[f"{source.file}.words.json"] = fmt.json_file(source.pdf_url, source.license, today, source.about,
                                                           words_response(words(pdf)))
    return files


def without_keys(value, keys):
    """The value with the given keys dropped from every dict in it, at any depth."""
    if isinstance(value, dict):
        return {key: without_keys(item, keys) for key, item in value.items() if key not in keys}
    if isinstance(value, list):
        return [without_keys(item, keys) for item in value]
    return value


def comparable(name, data, ignore_keys=()):
    """The lines of a recorded file with its Recorded date and the source's ignored keys left out,
    so a refetch on another day matches."""
    if data is None:
        return []
    if name.endswith(".json"):
        envelope = json.loads(data)
        envelope.pop("recorded", None)
        envelope["response"] = without_keys(envelope.get("response"), set(ignore_keys))
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
    parser = argparse.ArgumentParser(prog="python -m strata.fixture.record",
                                     description=" ".join(__doc__.split("\n\n")[0].split()))
    parser.add_argument("--write", action="store_true", help="Save the changes instead of only showing them.")
    parser.add_argument("--only", action="append", default=[], metavar="TEXT",
                        help="Record only the sources whose file name contains this text. You can repeat it.")
    parser.add_argument("--manifest", default=str(fmt.MANIFEST), metavar="PATH", help="The list of sources.")
    parser.add_argument("--max-lines", type=int, default=80, metavar="N",
                        help="The most diff lines to print for each file.")
    return parser.parse_args(argv)


def main(argv=None, fetch=fetch_url, words=pdf_words):
    args = parse(argv)
    manifest = fmt.load_manifest(args.manifest)
    sources = [s for s in manifest.sources if not args.only or any(part in s.file for part in args.only)]
    today = date.today().isoformat()
    counts = {"new": 0, "changed": 0, "same": 0}
    failed = []
    print(f"Fetching {count(len(sources), 'source')}. Recorded files are in {manifest.recorded}.")
    for source in sources:
        try:
            files = fetched_files(source, fetch, today, words)
        except Exception as error:  # noqa: BLE001 - report every failure, then carry on
            failed.append(source.file)
            print(f"could not fetch  {source.file}: {type(error).__name__}: {error}")
            continue
        for name, data in files.items():
            path = manifest.recorded / name
            old = path.read_bytes() if path.exists() else None
            before, after = (comparable(name, blob, source.ignore_keys) for blob in (old, data))
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
    fetched = "Every source was fetched." if not failed else f"{count(len(failed), 'source')} could not be fetched."
    print(f"{counts['new']} new, {counts['changed']} changed and {counts['same']} the same. {fetched}")
    if failed:
        print("To try those again, run: uv run python -m strata.fixture.record "
              + " ".join(f"--only {name}" for name in failed) + (" --write" if args.write else ""))
        return 2
    if pending and not args.write:
        print("Nothing was saved. Run again with --write to save these changes.")
        return 1
    if pending:
        print(f"Saved {count(pending, 'file')}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
