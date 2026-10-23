"""Building the fixture database: each CSV file in the placeholder folder becomes a table,
and a file whose name is not a table name stops the build before it writes anything."""

import importlib.util
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]


def builder():
    spec = importlib.util.spec_from_file_location("build_fixture", ROOT / "gates" / "build_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_fixture_file_whose_name_starts_with_an_underscore_stops_the_build(tmp_path):
    source = tmp_path / "placeholder"
    source.mkdir()
    (source / "_plan_rows.csv").write_text("plan_id\nP1\n")
    out = tmp_path / "fixture.duckdb"

    with pytest.raises(SystemExit, match="start with a letter"):
        builder().build(out=out, source=source, manifest=ROOT / "data" / "fixture" / "sources.toml")

    assert not out.exists()


MANIFEST = """
recorded = "recorded"

[datasets.awards]
attribution = "The World Bank: Contract Awards. License: CC BY 4.0."

[[source]]
file = "api/awards/P000001.json"
kind = "json"
dataset = "awards"
url = "https://awards.example/?project=P000001"
about = "Awards for P000001."

[[source]]
file = "documents/P000001/icr"
kind = "document"
dataset = "awards"
text_url = "https://documents.example/icr.txt"
pdf_url = "https://documents.example/icr.pdf"
about = "An ICR."
"""


def test_the_fixture_database_holds_every_recorded_file_with_its_source_license_and_pages(tmp_path):
    from strata.fixture import recorded as fmt

    (tmp_path / "sources.toml").write_text(MANIFEST)
    files = tmp_path / "recorded"
    (files / "api" / "awards").mkdir(parents=True)
    (files / "documents" / "P000001").mkdir(parents=True)
    (files / "api" / "awards" / "P000001.json").write_bytes(fmt.json_file(
        "https://awards.example/?project=P000001", "The World Bank: Contract Awards. License: CC BY 4.0.",
        "2026-10-23", "Awards for P000001.", {"data": [{"supplier_contract_amount_usd": 1245092.76}]}))
    header = {"License": "The World Bank: Contract Awards. License: CC BY 4.0.", "Recorded": "2026-10-23"}
    (files / "documents" / "P000001" / "icr.txt").write_bytes(fmt.text_file(
        {"Source": "https://documents.example/icr.txt", **header}, b"Published text"))
    (files / "documents" / "P000001" / "icr.pages.txt").write_bytes(fmt.text_file(
        {"Source": "https://documents.example/icr.pdf", **header}, b"First page\fSecond page"))
    placeholder = tmp_path / "placeholder"
    placeholder.mkdir()
    out = tmp_path / "fixture.duckdb"

    builder().build(out=out, source=placeholder, manifest=tmp_path / "sources.toml")

    with duckdb.connect(str(out), read_only=True) as con:
        licensed = con.execute("SELECT file, source, license FROM recorded.files ORDER BY file").fetchall()
        amount = con.execute("SELECT response->'$.data[0].supplier_contract_amount_usd' FROM recorded.responses"
                             ).fetchone()[0]
        pages = con.execute("SELECT pdf_page, text FROM recorded.pages ORDER BY pdf_page").fetchall()
    assert licensed == [
        ("api/awards/P000001.json", "https://awards.example/?project=P000001",
         "The World Bank: Contract Awards. License: CC BY 4.0."),
        ("documents/P000001/icr.pages.txt", "https://documents.example/icr.pdf",
         "The World Bank: Contract Awards. License: CC BY 4.0."),
        ("documents/P000001/icr.txt", "https://documents.example/icr.txt",
         "The World Bank: Contract Awards. License: CC BY 4.0."),
    ]
    assert amount == "1245092.76"
    assert pages == [(1, "First page"), (2, "Second page")]


def recorded_files(manifest):
    return {path.relative_to(manifest.recorded).as_posix()
            for path in manifest.recorded.rglob("*") if path.is_file()}


def test_every_recorded_file_is_listed_and_carries_its_source_and_a_cc_by_4_license_line():
    from strata.fixture import recorded as fmt

    manifest = fmt.load_manifest()
    listed = {name for source in manifest.sources for name in source.files()}

    assert recorded_files(manifest) == listed
    for name in sorted(listed):
        file = fmt.read(manifest.recorded / name)
        assert file.source.startswith("https://"), name
        assert file.license.startswith("The World Bank: ") and file.license.endswith("License: CC BY 4.0."), name
        assert file.recorded, name


def test_the_recorded_fixture_stays_inside_its_size_limits():
    import tomllib

    from strata.fixture import recorded as fmt

    manifest = fmt.load_manifest()
    limits = tomllib.loads(manifest.path.read_text())["limits"]
    sizes = {name: (manifest.recorded / name).stat().st_size / 1_000_000 for name in recorded_files(manifest)}

    assert max(sizes.values()) <= limits["file_mb"]
    assert sum(sizes.values()) <= limits["total_mb"]


def test_the_fixture_database_loads_every_recorded_file_with_no_network(fixture_db):
    from strata.fixture import recorded as fmt

    manifest = fmt.load_manifest()
    with duckdb.connect(str(fixture_db), read_only=True) as con:
        files = {row[0] for row in con.execute("SELECT file FROM recorded.files").fetchall()}
        icr_pages = con.execute("SELECT count(*) FROM recorded.pages WHERE document = ?",
                                ["documents/P130164/icr-2019-10-10"]).fetchone()[0]

    assert files == recorded_files(manifest)
    assert icr_pages == 66
