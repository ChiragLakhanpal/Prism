"""The first documents read into numbered passages: seam 1, the lakehouse run over the fixture.

The gate builds the fixture database by running the passage reader over the recorded documents
(gates/build_fixture.py), so most tests read what that run wrote. Every quoted paragraph, page and
section comes from tests/ground_truth/values.toml, which quotes the documents with their PDF pages,
or from the ticket, never from Strata's code.
"""

import re
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
ICR = "Implementation Completion and Results Report"


def value(key: str) -> dict:
    return next(entry for entry in GROUND_TRUTH["value"] if entry["id"] == key)


@pytest.fixture(scope="module")
def db(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


ICR_PARAGRAPH = """
SELECT p.*, d.pdf_pages
FROM strata.silver.passages AS p
JOIN strata.silver.documents AS d ON d.document_id = p.document_id
WHERE p.project_id = 'P130164' AND p.document_type = :document_type AND p.paragraph = :paragraph
"""


@pytest.mark.parametrize("key", ["icr-para-54", "icr-para-55", "icr-para-78"])
def test_each_showcase_icr_paragraph_is_exactly_one_passage_on_its_page_and_section_word_for_word(db, key):
    truth = value(key)

    found = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph=str(truth["paragraph"]))

    assert len(found) == 1, f"ICR ¶{truth['paragraph']} is {len(found)} passages"
    [passage] = found
    assert passage["text"] == truth["quote"] or truth["quote"] in passage["text"]
    assert (passage["pdf_page"], passage["section_path"], passage["printed_page"]) == (
        truth["pdf_page"], truth["section"], truth["printed_page"])
    assert passage["paragraph_numbered"] is True
    assert passage["pdf_pages"] == 66  # the ticket: "on PDF page 23 of 66"


def test_icr_paragraph_54_is_its_whole_paragraph_word_for_word(db):
    truth = value("icr-para-54")

    [passage] = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph="54")

    assert passage["text"] == truth["quote"]


def test_the_header_prepended_to_icr_paragraph_54_names_the_report_project_country_sector_section_and_page(db):
    [passage] = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph="54")

    assert passage["header"] == "ICR, P130164, India, roads, III.B, ¶54, p.23"  # the ticket's header, word for word


# The ten fields every passage keeps (docs/PLAN.md section 5), by their columns in silver.passages.
TEN_FIELDS = ("project_id", "document_type", "version", "public_from", "section_path", "paragraph", "pdf_page",
              "printed_page", "language", "parse_route")


def test_every_paragraph_has_all_ten_fields_filled(db):
    """A paragraph keeps the ten fields, from either route. A table row or summary has no printed page,
    and a notice's text has no page at all, so they are checked by their own tests below. A document that
    prints no page number on any page, such as P156634's restructuring paper, gives none either."""
    passages = rows(db, f"SELECT passage_id, document_id, kind, {', '.join(TEN_FIELDS)} FROM strata.silver.passages")
    paragraphs = [p for p in passages if p["kind"] == "paragraph"]
    unprinted = {row["document_id"] for row in rows(db, "SELECT document_id FROM strata.silver.document_page_routes "
                                                        "GROUP BY document_id HAVING count(printed_page) = 0")}

    assert len(paragraphs) > 0
    assert unprinted == {"33103725"}  # the restructuring paper; every other report prints its page numbers
    empty = [(p["passage_id"], name) for p in paragraphs for name in TEN_FIELDS if p[name] in (None, "")
             and not (name == "printed_page" and p["parse_route"] == "B")  # a scan's foot number can be unreadable
             and not (name == "printed_page" and p["document_id"] in unprinted)]
    assert empty == []
    assert {p["parse_route"] for p in passages} == {"A", "B"}
    assert {p["kind"] for p in passages} == {"paragraph", "table_row", "table_summary", "notice_text"}
    # The documents API lists each of them in English but one, the stress shelf's report in French.
    assert {p["language"] for p in passages} == {"en", "fr"}


REPORTS = """
SELECT d.project_id, d.document_type, d.document_date, d.text_paged, d.pdf_pages
FROM strata.silver.documents AS d
"""


def test_the_fixture_run_reads_every_recorded_report_of_the_slice_and_routes_the_scan_to_route_b(db):
    """Ticket 11 read the first twenty documents; ticket 18 reads the whole slice, which in the fixture is
    every report recorded for P130164, P156634 and P127203: 38 whose text Route A reads, one of them
    P156634's Project Paper, and one scan."""
    documents = rows(db, REPORTS)
    read = [d for d in documents if d["text_paged"]]
    dated = {(d["project_id"], d["document_type"], d["document_date"]) for d in read}
    recorded = sorted((ROOT / "data" / "fixture" / "recorded" / "documents").glob("*/*.pages.txt"))
    reports = [path for path in recorded if not path.name.startswith("procurement-plan")]

    assert len(documents) == len(reports) == 39
    assert len(read) == 38
    for key, document_type in [("icr-date", ICR), ("icr-review-date", "Implementation Completion Report Review"),
                               ("icr-review-reissue-date", "Implementation Completion Report Review"),
                               ("isr-7-date", "Implementation Status and Results Report"),
                               ("isr-12-date", "Implementation Status and Results Report")]:
        assert ("P130164", document_type, value(key)["value"]) in dated, key
    assert sum(d["document_type"] == "Implementation Status and Results Report" and d["project_id"] == "P130164"
               for d in read) == 13  # every ISR of P130164, all published as text
    assert ("P156634", "Project Appraisal Document") in {(d["project_id"], d["document_type"]) for d in read}
    [scan] = [d for d in documents if not d["text_paged"]]
    assert (scan["project_id"], scan["document_type"]) == ("P130164", "Project Appraisal Document")
    routes = rows(db, "SELECT route, count(*) AS pages FROM strata.silver.document_page_routes "
                      "WHERE project_id = 'P130164' AND document_id = (SELECT document_id FROM strata.silver.documents "
                      "WHERE NOT text_paged) GROUP BY route")
    assert routes == [{"route": "B", "pages": scan["pdf_pages"]}]


def measured(engine, subject: str) -> dict[str, dict]:
    found = rows(engine, "SELECT * FROM strata.ops.data_readiness WHERE run_id = 'fixture' AND source = 'documents' "
                         "AND subject = :subject", subject=subject)
    return {row["measure"]: row for row in found}


def test_strata_ops_shows_pages_per_route_and_the_share_whose_paragraph_numbering_was_found(db):
    for project_id in ("P130164", "P156634"):
        found = measured(db, project_id)
        pages = rows(db, "SELECT sum(pdf_pages) AS n FROM strata.silver.documents WHERE project_id = :p",
                     p=project_id)[0]["n"]

        route_a, route_b = found["document_pages_route_a"], found["document_pages_route_b"]
        assert route_a["denominator"] == route_b["denominator"] == pages
        assert route_a["count"] + route_b["count"] == pages
        numbering = found["document_pages_paragraph_numbering_found"]
        assert 0 < numbering["count"] < numbering["denominator"] <= route_a["count"]
        assert all(row["detail"] for row in found.values())
    # P130164's 100-page PAD is a scan, so every one of its pages waits for Route B.
    assert measured(db, "P130164")["document_pages_route_b"]["count"] >= 100


# The table's reading rule (src/strata/lakehouse/tables/ops/data_readiness.sql): for each source,
# subject and measure, the row from the latest run that wrote that measure.
LATEST_PER_MEASURE = """
SELECT measure, run_id FROM (
  SELECT measure, run_id,
         row_number() OVER (PARTITION BY source, subject, measure ORDER BY measured_at DESC) AS newest
  FROM strata.ops.data_readiness WHERE source = 'documents' AND subject = :subject)
WHERE newest = 1
"""


def test_the_data_readiness_rule_keeps_the_plan_readers_and_the_passage_readers_measures_for_one_project(db):
    plan_runs = {row["run_id"] for row in rows(db, "SELECT run_id FROM strata.ops.data_readiness "
                                                   "WHERE measure = 'plan_versions_read'")}

    latest = rows(db, LATEST_PER_MEASURE, subject="P156634")

    by_plans = {row["measure"] for row in latest if row["run_id"] in plan_runs}
    by_passages = {row["measure"] for row in latest if row["run_id"] not in plan_runs}
    assert {"plan_versions_read", "pages_read_route_a", "pages_read_route_b"} <= by_plans
    assert {"passages_screened", "document_pages_route_a", "document_pages_route_b",
            "documents_read_route_a_text"} <= by_passages


ISR = "Implementation Status and Results Report"
NUMBERED_BODY = """
SELECT count(*) AS pages FROM strata.silver.document_page_routes AS r
JOIN strata.silver.documents AS d ON d.document_id = r.document_id
WHERE r.project_id = :project_id AND r.route = 'A' AND r.reason = 'body' AND d.document_type <> :isr
"""


def test_the_numbering_share_counts_only_the_body_pages_of_reports_that_number_their_paragraphs(db):
    """An ISR numbers none of its paragraphs, so its pages would only lower the share."""
    for project_id in ("P130164", "P156634"):
        numbering = measured(db, project_id)["document_pages_paragraph_numbering_found"]

        [body] = rows(db, NUMBERED_BODY, project_id=project_id, isr=ISR)
        assert numbering["denominator"] == body["pages"]
        assert numbering["count"] * 2 > numbering["denominator"]  # found on most pages of the ICR, ICR Reviews and PAD


def test_each_measure_says_what_it_counts_in_a_full_sentence_and_freshness_gives_the_sources_cadence(db):
    from strata.config import load_sources

    for project_id in ("P130164", "P156634"):
        found = measured(db, project_id)

        assert found["documents_fresh"]["detail"] == load_sources()["documents"].cadence
        counted = [row["detail"] for row in found.values() if row["kind"] != "fresh"]
        assert counted and all(detail.startswith("This counts ") and detail.endswith(".") for detail in counted)
        assert [detail for detail in counted if "strata." in detail or ", of " in detail] == []


def test_strata_ops_shows_the_documents_read_the_passages_linked_to_a_project_and_how_fresh_they_are(db):
    found = measured(db, "P130164")

    assert (found["documents_read_route_a_text"]["count"], found["documents_read_route_a_text"]["denominator"]) == (16, 17)
    linked = found["passages_linked_to_project"]
    assert linked["count"] == linked["denominator"] > 0  # gold.project holds P130164
    assert found["documents_fresh"]["as_of"] == value("icr-review-reissue-date")["value"]


def test_strata_ops_counts_the_documents_that_had_contact_details_taken_out_of_the_documents_fetched(db):
    """Each PAD's data sheet prints a contact (PAD_CONTACTS), and no other document fetched does. The
    run fetched P130164's ICR, two ICR Reviews, 13 ISRs and its PAD, and P156634's PAD, its restructuring
    paper of May 24, 2021 and 19 ISRs."""
    for project_id, documents in (("P130164", 17), ("P156634", 21)):
        removed = measured(db, project_id)["contact_details_removed"]

        assert (removed["kind"], removed["count"], removed["denominator"]) == ("stripped", 1, documents)


# The labelled contacts each recorded PAD's data sheet prints, counted by reading the files: P130164's
# gives a telephone number (its email is misread by the PDF's text layer and has no "@"), and
# P156634's gives a telephone number and an email.
PAD_CONTACTS = {"P130164/pad-2013-10-01": 1, "P156634/pad-2017-04-05": 2}


@pytest.mark.parametrize("document", sorted(PAD_CONTACTS))
def test_a_pads_labelled_phone_number_and_email_come_out_before_bronze_keeps_it(document):
    from strata.lakehouse import contacts

    published = (ROOT / "data" / "fixture" / "recorded" / "documents" / f"{document}.txt").read_text()

    kept, removed = contacts.strip_text(published)

    assert removed == PAD_CONTACTS[document]
    assert kept.count("[contact removed]") == PAD_CONTACTS[document]
    assert re.search(r"Telephone No\.:\s*\[contact removed\]", kept)


def test_the_only_documents_bronze_holds_with_contact_details_taken_out_are_the_two_pads(db):
    marked = rows(db, "SELECT DISTINCT t.project_id, l.document_type FROM strata.bronze.document_texts AS t "
                      "JOIN strata.silver.documents AS l ON l.document_id = t.document_id "
                      "WHERE t.text LIKE '%contact removed%' ORDER BY t.project_id")
    unread = rows(db, "SELECT count(*) AS n FROM strata.bronze.document_texts AS t WHERE t.text LIKE "
                      "'%contact removed%' AND t.document_id NOT IN (SELECT document_id FROM strata.silver.documents)")

    assert marked == [{"project_id": "P130164", "document_type": "Project Appraisal Document"},
                      {"project_id": "P156634", "document_type": "Project Appraisal Document"}]
    assert unread == [{"n": 0}]


def test_every_passage_has_a_stored_prompt_shields_result(db):
    found = rows(db, "SELECT p.passage_id, s.shield, s.attack_detected FROM strata.silver.passages AS p "
                     "LEFT JOIN strata.silver.passage_shields AS s ON s.text_hash = p.text_hash")

    assert found and all(row["attack_detected"] is not None and row["shield"] for row in found)
    for project_id in ("P130164", "P156634"):
        screened, hits = (measured(db, project_id)[name] for name in ("passages_screened",
                                                                       "passages_prompt_shields_hit"))
        assert screened["count"] == screened["denominator"] == hits["denominator"] > 0
        assert (hits["kind"], hits["count"]) == ("screened", 0)


@pytest.fixture
def fresh():
    from strata.lakehouse import catalog

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def test_a_prompt_shields_hit_is_kept_with_its_result_and_counted_in_data_readiness(
        fresh, shield_finding_an_attack_in):
    from strata.config import load_thresholds
    from strata.lakehouse import passages

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 3  # the ICR Reviews and the ICR: enough for paragraph 54
    report = passages.run_on_fixture(fresh, projects=["P130164"], thresholds=limits,
                                     shield=shield_finding_an_attack_in(value("icr-para-54")["quote"]))

    attacks = rows(fresh, "SELECT p.paragraph, p.document_type, s.attack_detected, s.detail "
                          "FROM strata.silver.passages AS p JOIN strata.silver.passage_shields AS s "
                          "ON s.text_hash = p.text_hash WHERE s.attack_detected")
    assert attacks == [{"paragraph": "54", "document_type": ICR, "attack_detected": True,
                        "detail": "found by the test"}]
    hits = rows(fresh, "SELECT count, denominator FROM strata.ops.data_readiness WHERE run_id = :run_id "
                       "AND measure = 'passages_prompt_shields_hit'", run_id=report.run_id)
    assert hits == [{"count": 1, "denominator": report.passages}]


def test_every_passage_sits_in_gold_with_a_vector_of_the_model_files_size_made_with_its_header(db):
    import hashlib

    from strata.config import load_models

    size = load_models()["embed"].dimensions
    silver = rows(db, "SELECT passage_id FROM strata.silver.passages")
    gold = {row["passage_id"]: row for row in rows(db, "SELECT passage_id, embedding, embedding_model, public_from "
                                                       "FROM strata.gold.passage")}

    assert set(gold) == {row["passage_id"] for row in silver}
    assert {len(row["embedding"]) for row in gold.values()} == {size}
    for project_id in ("P130164", "P156634"):
        embedded = measured(db, project_id)["passages_embedded"]
        assert embedded["count"] == embedded["denominator"] > 0
    [passage] = rows(db, ICR_PARAGRAPH, document_type=ICR, paragraph="54")
    # What was embedded is the ticket's header, a line break, then the paragraph word for word.
    embedded = "ICR, P130164, India, roads, III.B, ¶54, p.23\n" + value("icr-para-54")["quote"]
    vectors = rows(db, "SELECT model FROM strata.silver.passage_embeddings WHERE text_hash = :hash",
                   hash=hashlib.sha256(embedded.encode("utf-8")).hexdigest())
    assert [row["model"] for row in vectors] == [gold[passage["passage_id"]]["embedding_model"]]


class CountingEmbedder:
    """The offline stand-in, counting the passages it is asked to embed."""

    def __init__(self):
        from strata.knowledge.embed import offline

        self.inner, self.embedded = offline(), 0
        self.name, self.dimensions = self.inner.name, self.inner.dimensions

    def embed(self, texts):
        self.embedded += len(texts)
        return self.inner.embed(texts)


def test_a_second_run_fetches_parses_and_embeds_nothing_new(fresh):
    from strata.config import load_thresholds
    from strata.lakehouse import passages

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 2
    first, second = CountingEmbedder(), CountingEmbedder()
    passages.run_on_fixture(fresh, projects=["P130164"], thresholds=limits, embedder=first)
    held = rows(fresh, "SELECT (SELECT count(*) FROM strata.bronze.document_texts) AS texts, "
                       "(SELECT count(*) FROM strata.gold.passage) AS indexed")
    passages.run_on_fixture(fresh, projects=["P130164"], thresholds=limits, embedder=second)

    assert first.embedded > 0 and second.embedded == 0
    assert rows(fresh, "SELECT (SELECT count(*) FROM strata.bronze.document_texts) AS texts, "
                       "(SELECT count(*) FROM strata.gold.passage) AS indexed") == held


class UndatedReissue:
    """The recorded documents, but the list gives the ICR Review's May 4, 2023 re-issue no disclosure
    date, and its text is fetched two days after the list, as a live run on another day would fetch it."""

    def __init__(self, inner):
        self.inner, self.text_url = inner, None

    def listing(self, url):
        import copy

        from strata.reader.documents import Fetched

        fetched = self.inner.listing(url)
        body = copy.deepcopy(fetched.body)
        for document in body.get("documents", {}).values():
            if (isinstance(document, dict) and document.get("docty") == "Implementation Completion Report Review"
                    and document["docdt"].startswith(str(value("icr-review-reissue-date")["value"]))):
                document.pop("disclosure_date")
                self.text_url = document["txturl"]
        return Fetched(url, body, fetched.fetched_at)

    def text(self, url):
        import datetime as dt

        from strata.reader.documents import Fetched

        fetched = self.inner.text(url)
        later = fetched.fetched_at + dt.timedelta(days=2) if url == self.text_url else fetched.fetched_at
        return Fetched(url, fetched.body, later)

    def pages(self, url):
        return self.inner.pages(url)


def test_a_re_issue_with_no_disclosure_date_replaces_the_earlier_version_on_its_own_public_date(fresh):
    """Otherwise the earlier version stops being current on the day the list was fetched, and the
    re-issue starts on the day its text was fetched, and for the days between neither is current."""
    from strata.config import load_thresholds
    from strata.fixture import recorded as fmt
    from strata.knowledge.embed import offline
    from strata.knowledge.shields import PatternShield
    from strata.lakehouse import passages
    from strata.reader.documents import RecordedDocuments

    limits = load_thresholds()
    limits.values["ingestion"]["passage_documents"] = 2  # the ICR Review and its re-issue come first
    passages.run(fresh, UndatedReissue(RecordedDocuments(fmt.load_manifest())), ["P130164"], thresholds=limits,
                 shield=PatternShield(), embedder=offline())

    first, reissue = rows(fresh, "SELECT version, public_from, replaced_on, (SELECT max(fetched_at) FROM "
                                 "strata.bronze.document_lists) AS listed_at FROM strata.silver.documents "
                                 "WHERE document_type = 'Implementation Completion Report Review' ORDER BY version")
    assert reissue["public_from"] > first["listed_at"].date()  # its text came two days after the list
    assert (first["replaced_on"], reissue["replaced_on"]) == (reissue["public_from"], None)


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def recorded_pages(document: str, first: int, last: int) -> str:
    """The text of PDF pages first to last as the recording read them from the PDF, not as Route A did."""
    from strata.fixture import recorded as fmt

    pages = fmt.pages(ROOT / "data" / "fixture" / "recorded" / f"{document}.pages.txt")
    return " ".join(pages[first - 1:last])


def test_a_paragraph_over_500_tokens_becomes_passages_divided_at_sentence_ends_that_share_its_number(db):
    from strata.reader.passages import tokens

    start, end = value("icr-review-2020-item-10a-start"), value("icr-review-2020-item-10a-end")

    parts = rows(db, "SELECT p.* FROM strata.silver.passages AS p "
                     "JOIN strata.silver.documents AS d ON d.document_id = p.document_id "
                     "WHERE d.project_id = :project AND d.document_type = :document_type AND d.document_date = :date "
                     "AND p.paragraph = :paragraph ORDER BY p.part", project=start["project"],
                 document_type=start["document_type"], date=start["date"], paragraph=start["paragraph"])

    assert len(parts) >= 2
    assert {(p["paragraph"], p["section_path"], p["parts"]) for p in parts} == {
        (start["paragraph"], start["section"], len(parts))}
    assert [p["part"] for p in parts] == list(range(1, len(parts) + 1))
    whole = " ".join(p["text"] for p in parts)
    assert tokens(whole) > 500 and all(p["tokens"] <= 500 for p in parts)
    assert all(re.search(r"[.!?][\"'”’)]*$", p["text"]) for p in parts), "a part ends inside a sentence"
    assert whole.startswith("a. " + start["value"]) and whole.endswith(end["quote"])
    assert (parts[0]["pdf_page"], parts[-1]["last_pdf_page"]) == (start["pdf_page"], end["pdf_page"])
    # Every word between the item's heading on page 11 and its last sentence on page 12, as the PDF has them.
    page_12 = squash(recorded_pages(end["document"], end["pdf_page"], end["pdf_page"]))
    body = page_12[page_12.index(squash("The project was classified")):
                   page_12.index(squash(end["quote"])) + len(squash(end["quote"]))]
    assert squash(whole) == squash("a. " + start["value"]) + body
