"""Exporting review notes at seam 3 (ticket 35): the Word file with one footnote per citation, the evidence pack
as a PDF and a CSV listing every source and whether its author opened it, and no call out of Strata.

The draft is written by the scripted writer on the fixture database, as in tests/test_drafts.py, checked and
exported through the routes. The files are read back as a person's software would: the Word file as the
zip of XML parts Word reads, the PDF with pypdf and the CSV with Python's csv module.

The expected source line is the plan's, from independent sources: the agency, the plan's date and its PDF
page from tests/ground_truth/values.toml, and the plan's public address from check_plan's recorded answer.
"""

import csv
import io
import re
import socket
import zipfile
from xml.etree import ElementTree

import pytest
from pypdf import PdfReader

from test_drafts import (ANA, BEN, CHECKED, CY, MARKED, ROW_OF, TRUTH, act, call, clock, draft_review_notes,  # noqa: F401
                         drafting, open_source, state_db)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PLAN = TRUTH["plan"]
# "page" and its number are joined by a no-break space, so they never part at a line end (DESIGN.md section 7).
SOURCE_LINE = (f"Procurement Plan, Northern Water Works Development Agency, P156634, version of October 9, 2026, "
               f"page\u00a0{PLAN['pdf_page']}.")
# A CSV has no line ends to protect, and a search for "page 3" in a spreadsheet must find it: a plain space.
CSV_SOURCE_LINE = SOURCE_LINE.replace("\u00a0", " ")
PDF_URL = CHECKED["plan"]["pdf_url"]
STEM = "review-notes-P156634-northern-water-works-development-agency-2026-10-09"


@pytest.fixture
def exported(drafting, clock):
    """Review notes Ana checked and exported after opening the second activity's source."""
    app = drafting()
    _, draft_id = draft_review_notes(app)
    clock.move(minutes=2)
    open_source(app, ROW_OF[MARKED[1]])
    clock.move(minutes=2)
    act(app, draft_id, "check", "draft")
    clock.move(minutes=2)
    answer = act(app, draft_id, "export", "checked")
    assert answer.status_code == 200
    return app, draft_id, answer.json()


def download(app, draft_id, name, headers=ANA):
    return call(app, "GET", f"/api/drafts/{draft_id}/files/{name}", headers)


def test_export_makes_a_word_file_with_one_footnote_per_citation_and_the_success_state_names_it(exported):
    app, draft_id, draft = exported
    citations = [evidence for note in draft["notes"] for sentence in note["sentences"] for evidence in sentence["evidence_ids"]]

    word = download(app, draft_id, f"{STEM}.docx")

    assert word.status_code == 200
    assert word.headers["content-disposition"] == f'attachment; filename="{STEM}.docx"'
    parts = zipfile.ZipFile(io.BytesIO(word.content))
    document = ElementTree.fromstring(parts.read("word/document.xml"))
    footnotes = ElementTree.fromstring(parts.read("word/footnotes.xml"))
    references = [int(ref.get(f"{W}id")) for ref in document.iter(f"{W}footnoteReference")]
    notes = {int(note.get(f"{W}id")): "".join(text.text for text in note.iter(f"{W}t")).strip()
             for note in footnotes.iter(f"{W}footnote") if int(note.get(f"{W}id")) > 0}
    # One footnote per citation, in order, each the source line of the row it cites and the plan's address.
    assert references == list(range(1, len(citations) + 1)) == sorted(notes)
    assert all(notes[number] == f"{SOURCE_LINE} {PDF_URL}" for number in references)
    # The success state names the file and its footnote count.
    assert draft["export"]["footnotes"] == len(citations) == draft["citations"]
    assert [file["name"] for file in draft["export"]["files"]] == [
        f"{STEM}-evidence-pack.csv", f"{STEM}-evidence-pack.pdf", f"{STEM}.docx"]


def test_the_word_file_has_the_two_columns_each_activity_and_its_origin_in_word_s_built_in_styles(exported):
    app, draft_id, _ = exported
    parts = zipfile.ZipFile(io.BytesIO(download(app, draft_id, f"{STEM}.docx").content))
    document = ElementTree.fromstring(parts.read("word/document.xml"))
    rows = [["".join(text.text for text in cell.iter(f"{W}t")) for cell in row.iter(f"{W}tc")]
            for row in document.iter(f"{W}tr")]
    paragraphs = ["".join(text.text for text in p.iter(f"{W}t")) for p in document.find(f"{W}body").findall(f"{W}p")]
    styles = parts.read("word/styles.xml").decode()

    assert rows[0] == ["Activity", "Review note"]
    assert [row[0][:len(ref)] for row, ref in zip(rows[1:], MARKED, strict=True)] == MARKED
    assert paragraphs[0] == "Review notes on the Northern Water Works Development Agency plan of October 9, 2026"
    assert paragraphs[2].startswith("Drafted with Strata on October 23, 2026 and checked by Ana Example on October 23, 2026.")
    assert paragraphs[2].endswith("These notes are not a World Bank review, clearance or no-objection.")
    assert 'w:ascii="Arial"' in styles and '<w:sz w:val="22"/>' in styles and "Table Grid" in styles


def test_the_evidence_pack_lists_every_source_and_whether_its_author_opened_it_as_a_pdf_and_a_csv(exported):
    app, draft_id, draft = exported

    pdf = PdfReader(io.BytesIO(download(app, draft_id, f"{STEM}-evidence-pack.pdf").content))
    table = list(csv.reader(io.StringIO(download(app, draft_id, f"{STEM}-evidence-pack.csv").content.decode())))

    text = " ".join(" ".join(page.extract_text().split()) for page in pdf.pages)
    assert text.startswith("Evidence pack")
    assert "Ana Example opened 1 of 3 sources before exporting." in text
    assert "Not checked:" in text and "The World Bank does not guarantee the accuracy of the data." in text
    fonts = {font.get_object()["/BaseFont"] for page in pdf.pages for font in page["/Resources"]["/Font"].values()}
    assert any(name.endswith("+OpenSans") for name in fonts)
    assert table[0] == ["Number", "Evidence ID", "Source", "Cited in", "Opened before export", "Last opened (UTC)",
                        "Kept another source", "Reason"]
    assert [(row[0], row[1], row[2], row[3], row[4]) for row in table[1:]] == [
        (str(number), ROW_OF[ref], CSV_SOURCE_LINE, ref, "Yes" if ref == MARKED[1] else "No")
        for number, ref in enumerate(MARKED, 1)]
    # The column heading says UTC, so each moment does not repeat it.
    assert table[2][5] == "October 23, 2026, 14:02" and table[1][5] == table[3][5] == ""
    assert draft["export"]["opened"] == 1 and draft["export"]["sources"] == 3


def test_an_evidence_pack_row_with_a_comma_a_quote_and_a_line_break_reads_back_cell_for_cell():
    """Moved from the web app's export test (ticket 35): the server writes the CSV now. A reason a person
    gives for keeping another source (ticket 23) is free text, so it may hold any of these."""
    from strata.drafts.files import pack_csv

    reason = 'The ICR says "108 of 328", and\nthe ISR agrees'
    row = {"number": 1, "evidence_id": ROW_OF[MARKED[0]], "source": SOURCE_LINE, "cited_in": MARKED[:2], "opened": True,
           "last_opened_at": "2026-10-23T14:02:00Z", "kept_another": True, "reason": reason}

    written = pack_csv([row]).decode()

    assert written.endswith("\r\n") and "\r\n" in written.split("Reason", 1)[1]
    assert list(csv.reader(io.StringIO(written)))[1] == [
        "1", ROW_OF[MARKED[0]], CSV_SOURCE_LINE, f"{MARKED[0]}, {MARKED[1]}", "Yes", "October 23, 2026, 14:02", "Yes", reason]


def test_the_files_go_to_the_author_s_team_and_no_one_else(exported):
    app, draft_id, _ = exported

    assert download(app, draft_id, f"{STEM}.docx", BEN).status_code == 200
    assert download(app, draft_id, f"{STEM}.docx", CY).status_code == 404
    assert download(app, draft_id, "not-a-file.docx").status_code == 404


def test_export_makes_no_call_out_of_strata_and_only_offers_the_files(drafting, monkeypatch):
    """The root conftest refuses every connection outside this computer, so relying on it alone would pass
    even if export tried one and hid the error. These spies record any attempt at all, local or not."""
    app = drafting()
    _, draft_id = draft_review_notes(app)
    act(app, draft_id, "check", "draft")
    attempts = []
    connect, lookup = socket.socket.connect, socket.getaddrinfo

    def spy_connect(self, address, *args, **kwargs):
        attempts.append(("connect", address))
        return connect(self, address, *args, **kwargs)

    def spy_lookup(host, *args, **kwargs):
        attempts.append(("getaddrinfo", host))
        return lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", spy_connect)
    monkeypatch.setattr(socket, "getaddrinfo", spy_lookup)

    exported = act(app, draft_id, "export", "checked")

    assert exported.status_code == 200 and exported.json()["state"] == "exported"
    assert attempts == []
    # The answer offers the files by name, for the browser to download from Strata's own server.
    assert all(re.fullmatch(rf"{STEM}(-evidence-pack)?\.(docx|pdf|csv)", file["name"])
               for file in exported.json()["export"]["files"])
