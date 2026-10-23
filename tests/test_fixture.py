"""Building the fixture database and checking the recorded files. A table definition DuckDB cannot
run, or a plan the plan reader cannot fetch, stops the build before it writes anything. Every
recorded file is listed in sources.toml with its source and license line, the files stay inside
their size limits, and every response stamped with a daily as_of_date leaves it out of the refresh
diff."""

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


def test_a_project_whose_document_list_was_never_recorded_stops_the_build_with_one_sentence(tmp_path):
    from strata.fixture import recorded as fmt

    (tmp_path / "sources.toml").write_text('recorded = "recorded"\n')
    out = tmp_path / "fixture.duckdb"

    with pytest.raises(SystemExit, match="no recording of https://search.worldbank.org/api/v3/wds") as stopped:
        builder().build(out=out, manifest=fmt.load_manifest(tmp_path / "sources.toml"), plans_for="P156634")

    assert isinstance(stopped.value.code, str)
    assert not out.exists()


def test_a_table_definition_duckdb_cannot_run_stops_the_build_with_one_sentence(tmp_path):
    tables = tmp_path / "tables" / "ops"
    tables.mkdir(parents=True)
    (tables / "pipeline_runs.sql").write_text(
        "CREATE TABLE IF NOT EXISTS strata.ops.pipeline_runs (run_id STRING COMMENT 'the run', public_from DATE)\n")
    out = tmp_path / "fixture.duckdb"

    with pytest.raises(SystemExit, match="transpile step could not rewrite") as stopped:
        builder().build(out=out, tables=tmp_path / "tables")

    assert isinstance(stopped.value.code, str)
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
    out = tmp_path / "fixture.duckdb"

    builder().build(out=out, manifest=fmt.load_manifest(tmp_path / "sources.toml"), plans_for=None)

    with duckdb.connect() as con:
        con.execute("ATTACH ? AS strata (READ_ONLY)", [str(out)])
        licensed = con.execute("SELECT file, source, license FROM strata.recorded.files ORDER BY file").fetchall()
        amount = con.execute("SELECT response->'$.data[0].supplier_contract_amount_usd' "
                             "FROM strata.recorded.responses").fetchone()[0]
        pages = con.execute("SELECT pdf_page, text FROM strata.recorded.pages ORDER BY pdf_page").fetchall()
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
    listed = manifest.files()

    assert recorded_files(manifest) == set(listed)
    assert len(listed) == len(set(listed)), "a recorded file is listed twice in sources.toml"
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
    with duckdb.connect() as con:
        con.execute("ATTACH ? AS strata (READ_ONLY)", [str(fixture_db)])
        files = {row[0] for row in con.execute("SELECT file FROM strata.recorded.files").fetchall()}
        icr_pages = con.execute("SELECT count(*) FROM strata.recorded.pages WHERE document = ?",
                                ["documents/P130164/icr-2019-10-10"]).fetchone()[0]

    assert files == recorded_files(manifest)
    assert icr_pages == 66


def stamped(value, key):
    """True when any dict in the value, at any depth, has the key."""
    if isinstance(value, dict):
        return key in value or any(stamped(item, key) for item in value.values())
    if isinstance(value, list):
        return any(stamped(item, key) for item in value)
    return False


def test_every_recorded_response_stamped_with_a_daily_as_of_date_leaves_it_out_of_the_refresh_diff():
    from strata.fixture import recorded as fmt

    manifest = fmt.load_manifest()
    stamped_sources = [source for source in manifest.sources if source.kind == "json"
                       and stamped(fmt.read(manifest.recorded / source.file).body, "as_of_date")]

    assert stamped_sources, "no recorded response has an as_of_date, so this test checks nothing"
    assert [s.file for s in stamped_sources if "as_of_date" not in s.ignore_keys] == []
