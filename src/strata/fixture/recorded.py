"""The list of recorded sources and the formats of the files they are recorded in.

data/fixture/sources.toml lists every source once: where it comes from, the file it is
recorded in, and the dataset whose attribution and license line the file carries. Two
formats hold what comes back:

- An API response is a JSON file with the keys source, license, recorded, about and
  response. The response is the parsed JSON the API returned.
- A document is two text files. `<file>.txt` holds the text the World Bank publishes,
  byte for byte. `<file>.pages.txt` holds the text of each PDF page, one page after each
  form feed, so page n is the nth part. Both start with header lines (Source, License,
  Recorded, About) and a blank line.
"""

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data" / "fixture" / "sources.toml"
KINDS = ("json", "document")
HEADER_KEYS = ("Source", "License", "Recorded", "About", "Pages")
PAGE_BREAK = "\f"


@dataclass(frozen=True)
class Source:
    """One entry in sources.toml."""

    file: str
    kind: str
    license: str
    about: str
    url: str = ""
    text_url: str = ""
    pdf_url: str = ""
    ignore_keys: tuple = ()  # keys a refetch leaves out of its diff, such as a stamp that moves daily

    def files(self):
        """The recorded files this source writes, relative to the recorded folder."""
        if self.kind == "json":
            return [self.file]
        return [f"{self.file}.txt", f"{self.file}.pages.txt"]


@dataclass(frozen=True)
class Manifest:
    path: Path
    recorded: Path
    sources: list = field(default_factory=list)

    def files(self):
        """Every recorded file the sources write, relative to the recorded folder, in listing order."""
        return [name for source in self.sources for name in source.files()]


@dataclass(frozen=True)
class Recorded:
    """A recorded file: where it came from, its license line, and what came back."""

    source: str
    license: str
    recorded: str
    about: str
    body: object


def load_manifest(path=MANIFEST):
    path = Path(path)
    with open(path, "rb") as handle:
        config = tomllib.load(handle)
    datasets = config.get("datasets", {})
    sources = []
    for entry in config.get("source", []):
        name = entry.get("file", "(no file)")
        if entry.get("kind") not in KINDS:
            raise SystemExit(f"The source {name} in {path} needs a kind: one of {', '.join(KINDS)}.")
        dataset = datasets.get(entry.get("dataset"))
        if not dataset or not dataset.get("attribution"):
            raise SystemExit(f"The source {name} in {path} names the dataset {entry.get('dataset')!r}, "
                             "which has no attribution line under [datasets].")
        urls = ("url",) if entry["kind"] == "json" else ("text_url", "pdf_url")
        if not all(entry.get(key) for key in urls):
            raise SystemExit(f"The source {name} in {path} needs {' and '.join(urls)}.")
        sources.append(Source(file=entry["file"], kind=entry["kind"], license=dataset["attribution"],
                              about=entry.get("about", ""), url=entry.get("url", ""),
                              text_url=entry.get("text_url", ""), pdf_url=entry.get("pdf_url", ""),
                              ignore_keys=tuple(dataset.get("ignore_keys", ()))))
    return Manifest(path=path, recorded=path.parent / config.get("recorded", "recorded"), sources=sources)


def json_file(source, license, recorded, about, response):
    """The bytes of a recorded API response."""
    envelope = {"source": source, "license": license, "recorded": recorded, "about": about,
                "response": response}
    return (json.dumps(envelope, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def text_file(header, body):
    """The bytes of a recorded text file: header lines, a blank line, then the body as received."""
    lines = "".join(f"{key}: {header[key]}\n" for key in HEADER_KEYS if header.get(key))
    return (lines + "\n").encode("utf-8") + body


def read(path):
    """Read a recorded file of either format."""
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix == ".json":
        envelope = json.loads(raw)
        return Recorded(envelope["source"], envelope["license"], envelope["recorded"],
                        envelope.get("about", ""), envelope["response"])
    head, _, body = raw.partition(b"\n\n")
    header = dict(line.split(": ", 1) for line in head.decode("utf-8").splitlines())
    text = body.decode("utf-8", errors="replace").removeprefix("﻿")
    return Recorded(header.get("Source", ""), header.get("License", ""), header.get("Recorded", ""),
                    header.get("About", ""), text)


def pages(path):
    """The text of each PDF page of a recorded document, so pages(path)[0] is PDF page 1."""
    return read(path).body.split(PAGE_BREAK)
