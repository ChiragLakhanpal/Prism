"""The recording command refetches every source in data/fixture/sources.toml, prints a diff
against what is recorded, and overwrites recorded files only when asked with --write.

These tests run it on a small manifest in a temporary folder, with a fetch function that
serves canned responses, so they never reach the network.
"""

import json

import pytest

from strata.fixture import record
from strata.fixture import recorded as fmt

PROJECT_URL = "https://search.example/api/v3/projects?format=json&id=P000001"
MANIFEST = f"""
recorded = "recorded"

[datasets.projects]
attribution = "The World Bank: Projects API. License: CC BY 4.0."

[[source]]
file = "api/projects/P000001.json"
kind = "json"
dataset = "projects"
url = "{PROJECT_URL}"
about = "The project record for P000001."
"""


def run(tmp_path, responses, *args, manifest=MANIFEST):
    path = tmp_path / "sources.toml"
    path.write_text(manifest)

    def fetch(url):
        answer = responses[url]
        if isinstance(answer, Exception):
            raise answer
        return answer

    return record.main(["--manifest", str(path), *args], fetch=fetch)


def recorded(tmp_path, name):
    return tmp_path / "recorded" / name


def test_a_new_source_shows_as_a_diff_and_nothing_is_written_without_write(tmp_path, capsys):
    code = run(tmp_path, {PROJECT_URL: b'{"id": "P000001", "closingdate": "2026-10-31"}'})

    out = capsys.readouterr().out
    assert code == 1
    assert '+  "closingdate": "2026-10-31"' in out
    assert "--write" in out
    assert not recorded(tmp_path, "api/projects/P000001.json").exists()


def test_write_saves_the_response_with_its_source_and_license_lines(tmp_path, capsys):
    code = run(tmp_path, {PROJECT_URL: b'{"id": "P000001"}'}, "--write")

    saved = json.loads(recorded(tmp_path, "api/projects/P000001.json").read_text())
    assert code == 0
    assert saved["source"] == PROJECT_URL
    assert saved["license"] == "The World Bank: Projects API. License: CC BY 4.0."
    assert saved["response"] == {"id": "P000001"}


def test_an_unchanged_source_shows_no_diff_and_keeps_its_recorded_date(tmp_path, capsys):
    run(tmp_path, {PROJECT_URL: b'{"id": "P000001"}'}, "--write")
    path = recorded(tmp_path, "api/projects/P000001.json")
    saved = json.loads(path.read_text())
    saved["recorded"] = "2026-01-02"
    path.write_text(json.dumps(saved, indent=1) + "\n")
    before = path.read_bytes()
    capsys.readouterr()

    code = run(tmp_path, {PROJECT_URL: b'{"id": "P000001"}'}, "--write")

    out = capsys.readouterr().out
    assert code == 0
    assert "0 new, 0 changed and 1 the same" in out
    assert path.read_bytes() == before


def test_a_changed_source_shows_the_changed_lines_and_keeps_the_old_file_until_write(tmp_path, capsys):
    run(tmp_path, {PROJECT_URL: b'{"closingdate": "2025-10-31"}'}, "--write")
    capsys.readouterr()

    code = run(tmp_path, {PROJECT_URL: b'{"closingdate": "2026-10-31"}'})

    out = capsys.readouterr().out
    saved = json.loads(recorded(tmp_path, "api/projects/P000001.json").read_text())
    assert code == 1
    assert '-  "closingdate": "2025-10-31"' in out
    assert '+  "closingdate": "2026-10-31"' in out
    assert saved["response"] == {"closingdate": "2025-10-31"}


TWO_SOURCES = MANIFEST + """
[[source]]
file = "api/projects/P000002.json"
kind = "json"
dataset = "projects"
url = "https://search.example/api/v3/projects?format=json&id=P000002"
about = "The project record for P000002."
"""


def test_a_source_that_cannot_be_fetched_is_named_with_the_command_to_retry_it(tmp_path, capsys):
    responses = {PROJECT_URL: OSError("connection refused"),
                 "https://search.example/api/v3/projects?format=json&id=P000002": b'{"id": "P000002"}'}

    code = run(tmp_path, responses, "--write", manifest=TWO_SOURCES)

    out = capsys.readouterr().out
    assert code == 2
    assert "could not fetch  api/projects/P000001.json" in out
    assert "--only api/projects/P000001.json --write" in out
    assert recorded(tmp_path, "api/projects/P000002.json").exists()


AWARDS_URL = "https://datacatalogapi.example/dexapps/fone/api/apiservice?datasetId=DS00005"
AWARDS = f"""
recorded = "recorded"

[datasets.awards]
attribution = "The World Bank: Contract Awards. License: CC BY 4.0."
ignore_keys = ["as_of_date"]

[[source]]
file = "api/awards/P000001.json"
kind = "json"
dataset = "awards"
url = "{AWARDS_URL}"
about = "The award rows for P000001."
"""


def award_rows(as_of_date, *signed):
    rows = [{"wb_contract_number": str(n), "contract_signing_date": day, "as_of_date": as_of_date}
            for n, day in enumerate(signed, 1)]
    return json.dumps({"data": rows}).encode("utf-8")


def test_a_refetch_that_moves_only_the_daily_as_of_date_shows_as_the_same(tmp_path, capsys):
    run(tmp_path, {AWARDS_URL: award_rows("22-Oct-2026", "03-Jan-2022")}, "--write", manifest=AWARDS)
    before = recorded(tmp_path, "api/awards/P000001.json").read_bytes()
    capsys.readouterr()

    code = run(tmp_path, {AWARDS_URL: award_rows("23-Oct-2026", "03-Jan-2022")}, manifest=AWARDS)

    out = capsys.readouterr().out
    assert code == 0
    assert "0 new, 0 changed and 1 the same" in out
    assert recorded(tmp_path, "api/awards/P000001.json").read_bytes() == before


def test_a_new_award_row_shows_in_the_diff_without_the_as_of_date_lines(tmp_path, capsys):
    run(tmp_path, {AWARDS_URL: award_rows("22-Oct-2026", "03-Jan-2022")}, "--write", manifest=AWARDS)
    capsys.readouterr()

    code = run(tmp_path, {AWARDS_URL: award_rows("23-Oct-2026", "03-Jan-2022", "22-Jun-2026")}, "--write",
               manifest=AWARDS)

    out = capsys.readouterr().out
    saved = json.loads(recorded(tmp_path, "api/awards/P000001.json").read_text())
    assert code == 0
    assert '+    "contract_signing_date": "22-Jun-2026"' in out
    assert "as_of_date" not in out
    assert {row["as_of_date"] for row in saved["response"]["data"]} == {"23-Oct-2026"}


def tiny_pdf(*pages):
    """A PDF whose pages each hold one line of text, written by hand so the test needs no PDF writer."""
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(pages)))
    objects = ["<< /Type /Catalog /Pages 2 0 R >>",
               f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, text in enumerate(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                       f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    out, offsets = "%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


DOCUMENT = """
recorded = "recorded"

[datasets.documents]
attribution = "The World Bank: Documents and Reports. License: CC BY 4.0."

[[source]]
file = "documents/P000001/icr"
kind = "document"
dataset = "documents"
text_url = "https://documents.example/icr.txt"
pdf_url = "https://documents.example/icr.pdf"
about = "An ICR."
"""


def test_a_document_is_recorded_as_its_published_text_and_the_text_of_each_pdf_page(tmp_path):
    published = "Paragraph one.\r\n\f54. Works estimates.\r\n".encode("utf-8")
    responses = {"https://documents.example/icr.txt": published,
                 "https://documents.example/icr.pdf": tiny_pdf("Page one text", "Page two text")}

    code = run(tmp_path, responses, "--write", manifest=DOCUMENT)

    text = fmt.read(recorded(tmp_path, "documents/P000001/icr.txt"))
    pages = fmt.read(recorded(tmp_path, "documents/P000001/icr.pages.txt"))
    assert code == 0
    assert text.source == "https://documents.example/icr.txt"
    assert text.license == "The World Bank: Documents and Reports. License: CC BY 4.0."
    assert recorded(tmp_path, "documents/P000001/icr.txt").read_bytes().endswith(published)
    assert pages.source == "https://documents.example/icr.pdf"
    assert [page.strip() for page in fmt.pages(recorded(tmp_path, "documents/P000001/icr.pages.txt"))] == [
        "Page one text", "Page two text"]


@pytest.mark.parametrize("old, bad, message", [
    ('kind = "json"', 'kind = "csv"', "needs a kind"),
    ('dataset = "projects"', 'dataset = "awards"', "has no attribution line"),
])
def test_a_source_with_no_known_kind_or_no_license_line_stops_the_command(tmp_path, old, bad, message):
    with pytest.raises(SystemExit, match=message):
        run(tmp_path, {}, manifest=MANIFEST.replace(old, bad))
