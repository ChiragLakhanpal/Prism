"""Suggested PPSD risk rows at seam 3, through the HTTP routes (ticket 36, criteria 1 to 5).

"Suggest {n} PPSD risk rows" posts {"kind": "ppsd_rows", "package": ..., "criteria": ...} to /api/drafts. The server
reads the risks the viewer selected in section 3 itself, the suggest-PPSD-rows workflow runs the risk-table builder as
the viewer, the writer (the scripted writer, replaying tests/fixtures/agent/writers.toml) fills each row's Risk
Description and Description of mitigation, the verifier checks every sentence, and only then is the draft saved. The
story is tests/ppsd_story.py.

Expected values come from independent sources: the footnote forms from the ticket, the column names from the PPSD
templates (tests/ground_truth/values.toml, ppsd-*), the counts from the risk table's own recorded answer
(tests/fixtures/api/risks-ke-nwwda-541055-india.json) and the passages from values.toml (icr-para-54 and
icr-review-2023-restates-para-54).
"""

import copy
import io
import json
import re
import tomllib
import zipfile
from pathlib import Path

import pytest

import ppsd_story as story_of
from strata.config import load_draft_kinds
from strata.drafts.store import DraftStore, NewDraft
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
RISK_TABLE = json.loads((ROOT / "tests" / "fixtures" / "api" / "risks-ke-nwwda-541055-india.json").read_text())
COUNT_FOOTNOTE = "Seen in {k} of {m} comparable completion reports."
SHORT = [VALUES[f"ppsd-short-{key}"]["value"] for key in ("risk-description", "mitigation", "risk-owner")]
LONG = [VALUES[f"ppsd-long-{key}"]["value"] for key in ("risk-description", "likelihood", "impact", "score", "mitigation",
                                                        "risk-owner", "stage")]
PEOPLE = ("risk_owner", "likelihood", "impact", "score", "stage")


@pytest.fixture(scope="module")
def database(fixture_db, tmp_path_factory):
    return story_of.library(fixture_db, tmp_path_factory.mktemp("ppsd-library"))


@pytest.fixture
def story(database, tmp_path):
    made = story_of.Story(database, tmp_path)
    assert made.select().status_code == 200
    return made


def suggested(story, case="ppsd-rows-ke-nwwda-541055") -> dict:
    sent, draft_id = story.suggest(case)
    assert draft_id, sent
    return story.get(f"/api/drafts/{draft_id}").json()


def word_parts(document: bytes) -> tuple[list[list[str]], list[str], str]:
    """The Word file's table, as rows of cell texts (a header cell's lines joined by a space), its footnotes' texts,
    and its body's text."""
    archive = zipfile.ZipFile(io.BytesIO(document))
    body = archive.read("word/document.xml").decode()
    notes = archive.read("word/footnotes.xml").decode()

    def text(xml: str) -> str:
        return " ".join(part for part in (
            "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", paragraph)) for paragraph in re.findall(r"<w:p>.*?</w:p>|<w:p/>", xml))
            if part).replace("&apos;", "'")

    table = re.search(r"<w:tbl>.*</w:tbl>", body).group()
    rows = [[text(cell) for cell in re.findall(r"<w:tc>.*?</w:tc>", row)] for row in re.findall(r"<w:tr>.*?</w:tr>", table)]
    footnotes = [text(note).strip() for note in re.findall(r'<w:footnote w:id="[1-9]\d*">.*?</w:footnote>', notes)]
    return rows, footnotes, text(body)


def test_the_screens_recorded_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """The draft screens' tests and the gallery serve these files; the routes must still answer with them."""
    from record_ppsd_api import answers

    for name, text in answers(tmp_path, fixture_db).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), (
            f"{name} is out of date: uv run --frozen python tests/record_ppsd_api.py")


# ── Criterion 1: rows that read like the Draft wireframe's, with footnotes from tools ─────

def test_the_selected_risks_become_rows_whose_footnotes_read_as_the_ticket_writes_them(story):
    draft = suggested(story)
    rows = draft["ppsd"]["rows"]

    assert [row["risk_key"] for row in rows] == [row["risk_key"] for row in RISK_TABLE["rows"]] == story_of.RISKS
    texts = [footnote["text"] for footnote in draft["footnotes"]]
    cost = RISK_TABLE["rows"][0]
    assert texts[0] == COUNT_FOOTNOTE.format(k=cost["k"], m=RISK_TABLE["m"])
    # The ticket's own footnote, from the cost estimates lesson's two passages (values.toml icr-para-54, page 23, and
    # the ICR Review's section 10.b).
    paragraph, page = VALUES["icr-para-54"]["paragraph"], VALUES["icr-para-54"]["pdf_page"]
    assert texts[1] == f"ICR P130164 ¶{paragraph}, page {page}; ICR Review {VALUES['icr-review-2023-restates-para-54']['paragraph']}."
    assert texts[1] == "ICR P130164 ¶54, page 23; ICR Review 10.b."
    assert draft["citations"] == len(draft["footnotes"]) == 4
    assert draft["removed"] == [] and draft["state"] == "draft"


def test_every_count_a_footnote_states_is_the_tool_s_and_each_marker_carries_its_sources(story):
    draft = suggested(story)
    summary_id = draft["ppsd"]["rows"][0]["counts_evidence_id"]
    summary = draft["evidence"][summary_id]

    assert summary["tool"] == "get_lessons"
    assert summary["row"]["reports"]["read"] == RISK_TABLE["m"]
    raised = {factor["key"]: factor["k"] for factor in summary["row"]["reports"]["risk_factors"]}
    for row in draft["ppsd"]["rows"]:
        assert (row["k"], row["m"]) == (raised[row["risk_key"]], summary["row"]["reports"]["read"])
    mitigation = draft["footnotes"][1]
    assert mitigation["evidence_ids"] == ["strata.ops.lesson_versions:lesson-e903b07ad1/v1",
                                          "strata.gold.passage:31525018/v1/54", "strata.gold.passage:34056616/v2/10.b"]
    assert draft["checks"]["checks_run"] == [1, 2, 3, 4, 5, 6]


def test_three_selected_risks_make_three_rows_each_with_its_own_footnotes(story, monkeypatch):
    """The fixture's completion reports raise two risks, so the risk table's third row is made up from the permits
    row and its records, for the shape only: three selected risks, three rows, six footnotes."""
    from strata.packages import risks

    build = risks.build

    def with_a_third(*args, **kwargs):
        table = build(*args, **kwargs)
        made_up = copy.deepcopy(table.payload["rows"][1])
        made_up.update(risk_key="contract_management", risk_label="Weak contract management")
        table.payload["rows"].append(made_up)
        return table

    monkeypatch.setattr(risks, "build", with_a_third)
    assert story.select(("contract_management",)).status_code == 200
    draft = suggested(story, "ppsd-rows-three-risks")

    assert [row["risk_key"] for row in draft["ppsd"]["rows"]] == [*story_of.RISKS, "contract_management"]
    assert draft["ppsd"]["selected"] == 3 and len(draft["footnotes"]) == 6
    assert draft["ppsd"]["counts"] == {"total": 3, "owners_set": 0, "rated": 0}


def test_a_selected_risk_that_dropped_out_of_the_table_is_not_drafted(story):
    """The person selected a risk the table no longer shows (the 30 brief, decision 4): only shown rows are drafted."""
    assert story.select(("contract_management",)).status_code == 200
    draft = suggested(story)

    assert [row["risk_key"] for row in draft["ppsd"]["rows"]] == story_of.RISKS
    assert draft["ppsd"]["selected"] == 2


def test_with_no_selected_risk_still_in_the_table_nothing_is_drafted(database, tmp_path):
    made = story_of.Story(database, tmp_path)
    assert made.select(("contract_management",)).status_code == 200
    sent, draft_id = made.suggest()

    assert draft_id is None
    assert ("error", {"code": "no_selected_risks"}) in sent


PLANNED = "pkg-000000000036"
# A package Ana planned from a sentence: the demo works package's Description, with India as its country, so that,
# as on the STEP row, its comparables reach P130164's completion report.
PLANNED_CRITERIA = {"values": {
    "category": {"value": "Works", "provenance": "sentence"},
    "description": {"value": "Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply",
                    "provenance": "sentence"},
    "country": {"value": "IN", "provenance": "you"},
    "method": {"value": "Request for Bids", "provenance": "sentence"}}}


def test_a_package_planned_from_a_sentence_suggests_rows_from_its_saved_criteria_and_only_for_its_author(
        story, monkeypatch):
    """The package workspace opened from "Plan a package from a sentence" posts {"kind": "ppsd_rows", "package":
    "pkg-..."} with no criteria: the route reads them, and the selection, from the author's saved package. A planned
    package's comparables start at past_range.period_from, after P130164's notices, so the builder here also looks
    from 2013, as section 1's country chip does for the STEP row."""
    import datetime as dt

    from strata.packages import risks
    from strata.packages.store import PackageStore

    build, given = risks.build, []

    def from_2013(*args, criteria=None, **kwargs):
        given.append((criteria, list(kwargs.get("selected") or ())))
        return build(*args, criteria={**criteria, "notice_from": "2013-01-01"} if criteria else criteria, **kwargs)

    monkeypatch.setattr(risks, "build", from_2013)
    PackageStore(lambda: DuckDBEngine.open(story.state_db)).create(
        PLANNED, "4021@1984", "Ana Example", "Equip the Tarbaj boreholes, in India", None, "save-0001", PLANNED_CRITERIA,
        dt.datetime(2026, 10, 28, 8, tzinfo=dt.UTC))
    selection = story.call("PUT", f"/api/planned-packages/{PLANNED}/risk-selection",
                           json={"changes": {risk: True for risk in story_of.RISKS}})
    assert selection.status_code == 200

    sent, draft_id = story.write("ppsd-rows-ke-nwwda-541055", {"kind": "ppsd_rows", "package": PLANNED,
                                                               "idempotency_key": "planned-1"})
    assert draft_id, sent
    draft = story.get(f"/api/drafts/{draft_id}").json()

    assert given[-1] == ({"category": "Works", "country": "IN", "method": "Request for Bids"}, story_of.RISKS)
    assert draft["subject"]["package_id"] == PLANNED and draft["subject"]["step_reference"] is None
    assert draft["subject"]["package_title"] == PLANNED_CRITERIA["values"]["description"]["value"]
    assert [row["risk_key"] for row in draft["ppsd"]["rows"]] == story_of.RISKS
    assert draft["removed"] == []
    assert story.get("/api/drafts/existing", kind="ppsd_rows", package=PLANNED).json()["draft"]["draft_id"] == draft_id

    # Ben, on the same team, cannot draft from Ana's planned package, nor learn that it exists.
    refused = story.call("POST", "/api/drafts", story_of.BEN,
                         json={"kind": "ppsd_rows", "package": PLANNED, "idempotency_key": "planned-ben"})
    assert (refused.status_code, refused.json()["code"]) == (404, "unknown_package")


def test_a_kind_registered_with_the_ppsd_rows_writer_is_prepared_as_ppsd_rows(database, tmp_path):
    """Ticket 38 registers the implementing agency's variant as one entry in config/drafts.toml with writer =
    "strata.drafts.ppsd_rows" (CLAUDE.md rule 9): the route prepares a kind by its writer, not by its key."""
    registry = (ROOT / "config" / "drafts.toml").read_text()
    start = registry.index("[kinds.ppsd_rows]")
    entry = registry[start:registry.index("\n\n", start)].replace("[kinds.ppsd_rows]", "[kinds.ppsd_rows_variant]")
    path = tmp_path / "drafts.toml"
    path.write_text(registry.replace("[holds.notChecked]", f"{entry}\n\n[holds.notChecked]"))
    story = story_of.Story(database, tmp_path, kinds=load_draft_kinds(path))
    assert story.select().status_code == 200

    answer = story.call("POST", "/api/drafts", json={"kind": "ppsd_rows_variant", "package": story_of.PACKAGE,
                                                      "criteria": story_of.INDIA, "idempotency_key": "variant-1"})

    assert answer.headers["content-type"].startswith("text/event-stream"), answer.text
    sent = story_of.events(answer.text)
    assert [kind for kind, _ in sent if kind in ("draft", "error")] == ["draft"], sent


def test_a_row_with_one_failed_cell_stays_with_that_cell_empty(story):
    draft = suggested(story, "ppsd-rows-one-cell-fails")
    permits = next(note for note in draft["notes"] if note["key"] == "permits_before_award/mitigation")

    assert [row["risk_key"] for row in draft["ppsd"]["rows"]] == story_of.RISKS
    assert permits["state"] == "abstained" and permits["sentences"] == []
    assert [item["reason"] for item in draft["removed"]] == ["number_not_in_records"]
    assert len(draft["footnotes"]) == 3


def test_a_row_whose_two_cells_both_failed_is_left_out_and_its_sentences_are_shown_removed(story):
    draft = suggested(story, "ppsd-rows-a-row-removed")

    assert [row["risk_key"] for row in draft["ppsd"]["rows"]] == ["cost_estimates"]
    assert {item["reason"] for item in draft["removed"]} == {"id_not_returned"}
    assert len(draft["removed"]) == 2
    assert all(not note["key"].startswith("permits_before_award/") for note in draft["notes"])


# ── Criterion 2: the Short Form, and the Long Form only above Table I ─────

def test_the_short_form_shows_exactly_the_template_s_three_columns_and_no_long_form_below_table_i(story):
    draft = suggested(story)
    shown = draft["ppsd"]

    assert shown["form"] == "short"
    assert [column["header"] for column in shown["forms"]["short"]["columns"]] == SHORT == [
        "Risk Description", "Description of mitigation", "Risk Owner"]
    # KE-NWWDA-541055-CW-RFB's cost estimate, US$1,230,000.00 (values.toml plan_row), is below Table I's lowest works
    # threshold of US$50 million, so the Long Form is not offered and the route refuses it.
    assert shown["table_i"] == {"applies": False, "amount": "1230000.00", "threshold": "50000000.00", "currency": "USD",
                                "category": "Works", "risk_level": "High"}
    answer = story.call("PUT", f"/api/drafts/{draft['draft_id']}/form", json={"form": "long"})
    assert (answer.status_code, answer.json()["code"]) == (422, "form_not_offered")


def above_table_i(story, draft_id: str) -> str:
    """The same draft saved again with a cost estimate at Table I's works threshold, made up for the Long Form."""
    store = DraftStore(lambda: DuckDBEngine.open(story.state_db))
    saved = store.get(draft_id)
    content = copy.deepcopy(saved.content)
    content["ppsd"]["table_i"].update(applies=True, amount="60000000.00")
    store.create(NewDraft("draft-0099", saved.kind, saved.team_key, saved.author_id, saved.author_name, None,
                          saved.project_id, saved.subject, content, saved.created_at))
    return "draft-0099"


def test_above_table_i_the_long_form_adds_its_four_columns_empty_and_they_hold_export(story):
    draft = above_table_i(story, suggested(story)["draft_id"])
    changed = story.call("PUT", f"/api/drafts/{draft}/form", json={"form": "long"}).json()

    assert changed["ppsd"]["form"] == "long"
    assert [column["header"] for column in changed["ppsd"]["forms"]["long"]["columns"]] == LONG
    added = [column["key"] for column in changed["ppsd"]["forms"]["long"]["columns"]
             if column["header"] not in SHORT and column["filled_by"] == "people"]
    assert added == ["likelihood", "impact", "score", "stage"]
    assert all(entry["value"] is None for entry in changed["ppsd"]["values"])
    assert [(hold["key"], hold["left"]) for hold in changed["holds"]] == [("notChecked", 1), ("owners", 2), ("ratings", 2)]
    # The stage is optional; the three ratings hold export.
    for row in ("cost_estimates", "permits_before_award"):
        for field, value in (("risk_owner", "Implementing agency, procurement"), ("likelihood", "4"), ("impact", "3"),
                             ("score", "12")):
            assert story.set_field(draft, row, field, value).status_code == 200
    after = story.get(f"/api/drafts/{draft}").json()
    assert [hold["key"] for hold in after["holds"]] == ["notChecked"]
    assert after["ppsd"]["counts"] == {"total": 2, "owners_set": 2, "rated": 2}


@pytest.mark.parametrize("field, value, code", [
    ("likelihood", "6", "not_a_rating"), ("score", "26", "not_a_score"), ("score", "twelve", "not_a_score"),
    ("risk_owner", "   ", "empty"), ("risk_owner", "x" * 121, "too_long"), ("description", "Mine", "unknown_field"),
])
def test_a_value_outside_the_template_s_is_refused(story, field, value, code):
    draft = suggested(story)["draft_id"]
    answer = story.set_field(draft, "cost_estimates", field, value)

    assert (answer.status_code, answer.json()["code"]) == (422, code)


# ── Criterion 3: Strata never writes an owner, a rating, a reference or an actual date ─────

def test_strata_never_writes_a_risk_owner_a_rating_a_reference_or_an_actual_date(story):
    """The writer answers with an owner, a likelihood, a reference and an actual date, in a cell it was never asked
    for and in fields of a cell it was. The draft keeps only Strata's two cells, every field people fill is empty, and
    nothing was saved in strata.ops.draft_fields: only the author's own session writes there."""
    draft = suggested(story, "ppsd-rows-writer-sets-an-owner")

    assert {note["key"].split("/")[1] for note in draft["notes"]} == {"risk_description", "mitigation"}
    assert all(entry["value"] is None for entry in draft["ppsd"]["values"])
    assert {entry["field"] for entry in draft["ppsd"]["values"]} == {"risk_owner"}
    stored = json.dumps(draft["notes"]) + json.dumps(draft["ppsd"]["rows"])
    for written in ("Implementing agency, procurement unit", "2026-11-30", "likelihood", "actual_date"):
        assert written not in stored
    with DuckDBEngine.open(story.state_db, read_only=True) as engine:
        assert engine.run("SELECT count(*) AS n FROM strata.ops.draft_fields").as_text() == [("0",)]
    from strata.config import load_ppsd_templates

    for form in load_ppsd_templates().forms.values():
        written = {column.key for column in form.columns if column.filled_by == "strata"}
        assert written == {"risk_description", "mitigation"}


def test_only_the_author_s_own_session_sets_a_field(story):
    draft = suggested(story)["draft_id"]

    assert story.set_field(draft, "cost_estimates", "risk_owner", "PIU", headers=story_of.BEN).json()["code"] == "not_author"
    assert story.set_field(draft, "cost_estimates", "risk_owner", "PIU", view="piu").json()["code"] == "preview"
    assert story.call("PUT", f"/api/drafts/{draft}/fields", headers={},
                      json={"row_key": "cost_estimates", "field": "risk_owner", "value": "PIU"}).status_code == 401
    assert story.get(f"/api/drafts/{draft}").json()["ppsd"]["counts"]["owners_set"] == 0


# ── Criterion 4: the owner count, and export held until every owner is set ─────

def test_the_owner_count_follows_each_owner_set_and_export_waits_for_every_owner(story):
    draft_id = suggested(story)["draft_id"]
    first = story.get(f"/api/drafts/{draft_id}").json()
    assert first["ppsd"]["counts"] == {"total": 2, "owners_set": 0, "rated": 0}
    assert [(hold["key"], hold["left"], hold["first_anchor"]) for hold in first["holds"]] == [
        ("notChecked", 1, None), ("owners", 2, "fill-cost_estimates-risk_owner")]

    one = story.set_field(draft_id, "cost_estimates", "risk_owner", "Implementing agency, procurement").json()
    assert one["ppsd"]["counts"]["owners_set"] == 1
    assert [(hold["key"], hold["left"], hold["first_anchor"]) for hold in one["holds"]] == [
        ("notChecked", 1, None), ("owners", 1, "fill-permits_before_award-risk_owner")]

    checked = story.act(draft_id, "check", "draft").json()
    assert checked["state"] == "checked" and [hold["key"] for hold in checked["holds"]] == ["owners"]
    held = story.act(draft_id, "export", "checked")
    assert (held.status_code, held.json()["code"], held.json()["holds"]) == (409, "held", ["owners"])

    # Owners stay open after checking, and a removal sends no value.
    removed = story.set_field(draft_id, "cost_estimates", "risk_owner", None).json()
    assert removed["ppsd"]["counts"]["owners_set"] == 0
    for row in story_of.RISKS:
        story.set_field(draft_id, row, "risk_owner", "Implementing agency, procurement")
    ready = story.get(f"/api/drafts/{draft_id}").json()
    assert ready["holds"] == [] and ready["ppsd"]["counts"]["owners_set"] == 2
    exported = story.act(draft_id, "export", "checked").json()
    assert exported["state"] == "exported"
    locked = story.set_field(draft_id, "cost_estimates", "risk_owner", "Someone else")
    assert (locked.status_code, locked.json()["code"]) == (409, "draft_state")


def test_the_drafts_tab_counts_the_owners_set(story):
    draft_id = suggested(story)["draft_id"]
    story.set_field(draft_id, "cost_estimates", "risk_owner", "Implementing agency, procurement")
    [row] = story.get("/api/drafts").json()["groups"]["to_check"]

    assert row["kind"] == "ppsd_rows"
    assert row["progress"] == {"total": 2, "owners_set": 1, "rated": 0, "form": "short", "rows": 2}


# P130164's efficiency, on which the ICR's paragraph 44 and the ICR Review disagree (strata.gold.disagreement in the
# fixture), and its PDO progress, a second disagreement for an info card.
DISAGREEMENT, OTHER_DISAGREEMENT = "51ea6e6516c0ea63", "437378890475ef48"


def test_a_warning_disagreement_holds_export_of_every_kind_until_its_author_keeps_a_report(database, tmp_path):
    """A warning card holds export, an info card holds nothing, and keeping either report through the card's own
    route (ticket 23's POST /api/disagreements/{id}/choices, with the draft's id) resolves it; a teammate's choice
    does not. The cards are made up on a real draft; the disagreements are the fixture's."""
    story = story_of.Story(database, tmp_path)
    story.select()
    draft_id = suggested(story)["draft_id"]
    store = DraftStore(lambda: DuckDBEngine.open(story.state_db))
    saved = store.get(draft_id)
    content = copy.deepcopy(saved.content)
    content["disagreements"] = [
        {"id": f"strata.gold.disagreement:{DISAGREEMENT}", "disagreement_id": DISAGREEMENT, "after": 0,
         "changes_answer": True, "sides": []},
        {"id": f"strata.gold.disagreement:{OTHER_DISAGREEMENT}", "disagreement_id": OTHER_DISAGREEMENT, "after": 1,
         "changes_answer": False, "sides": []}]
    store.create(NewDraft("draft-0098", saved.kind, saved.team_key, saved.author_id, saved.author_name, None,
                          saved.project_id, saved.subject, content, saved.created_at))
    with DuckDBEngine.open(database, read_only=True) as engine:
        lean, first, second = engine.run("SELECT lean_assertion_id, first_assertion_id, second_assertion_id "
                                         "FROM strata.gold.disagreement WHERE disagreement_id = :id",
                                         {"id": DISAGREEMENT}).rows[0]
    other = second if lean == first else first

    held = story.get("/api/drafts/draft-0098").json()["holds"]
    assert [(hold["key"], hold["left"], hold["first_anchor"]) for hold in held][-1] == (
        "disagreements", 1, f"disagreement-{DISAGREEMENT}")

    def keep(kept, reason="", headers=story_of.ANA):
        return story.call("POST", f"/api/disagreements/{DISAGREEMENT}/choices", headers,
                          json={"kept_assertion_id": kept, "reason": reason, "draft_id": "draft-0098"})

    assert (keep(other).status_code, keep(other).json()["code"]) == (422, "reason_required")
    assert keep(lean, headers=story_of.BEN).json()["recorded"] is True
    assert "disagreements" in [hold["key"] for hold in story.get("/api/drafts/draft-0098").json()["holds"]]

    assert keep(lean).json()["recorded"] is True
    kept = story.get("/api/drafts/draft-0098").json()
    assert "disagreements" not in [hold["key"] for hold in kept["holds"]]
    assert [(choice["disagreement_id"], choice["kept"]) for choice in kept["choices"]] == [(DISAGREEMENT, "lean")]

    assert keep(other, "The ICR Review read the same records later.").json()["recorded"] is True
    kept = story.get("/api/drafts/draft-0098").json()
    assert "disagreements" not in [hold["key"] for hold in kept["holds"]]
    assert [(choice["kept"], choice["reason"]) for choice in kept["choices"]] == [
        ("other", "The ICR Review read the same records later.")]
    # Ticket 23's card renders on every draft page, so a warning card holds as shipped.
    assert load_draft_kinds().cards_on_drafts is True


# ── Criterion 5: the Word file's table and footnotes ─────

def exported(story, case="ppsd-rows-ke-nwwda-541055") -> tuple[dict, bytes]:
    draft_id = suggested(story, case)["draft_id"]
    for row in story_of.RISKS:
        story.set_field(draft_id, row, "risk_owner", "Implementing agency, procurement")
    story.act(draft_id, "check", "draft")
    done = story.act(draft_id, "export", "checked").json()
    assert done["state"] == "exported", done
    return done, story.download(draft_id, ".docx")[1]


def test_the_word_file_has_the_template_s_headers_and_the_draft_s_footnotes(story):
    draft, document = exported(story)
    rows, footnotes, text = word_parts(document)

    assert rows[0] == SHORT
    assert footnotes == [footnote["text"] for footnote in draft["footnotes"]]
    assert draft["export"]["footnotes"] == len(footnotes) == 4
    # The owners are the author's own entries; Strata's cells hold its sentences.
    assert [row[2] for row in rows[1:]] == ["Implementing agency, procurement"] * 2
    assert rows[1][0].startswith("Cost estimates set below market rates can force rebidding")
    assert "Ana Example set the risk owners." in text
    assert "These are suggested rows for the borrower's PPSD and are not a World Bank review, clearance or no-objection." in text
    assert "Short Form." in text and "KE-NWWDA-541055-CW-RFB." in text


def test_the_long_form_s_word_table_keeps_the_template_s_seven_columns_in_its_order(story):
    draft_id = above_table_i(story, suggested(story)["draft_id"])
    story.call("PUT", f"/api/drafts/{draft_id}/form", json={"form": "long"})
    for row in story_of.RISKS:
        for field, value in (("risk_owner", "Implementing agency"), ("likelihood", "4"), ("impact", "3"), ("score", "12")):
            story.set_field(draft_id, row, field, value)
    story.act(draft_id, "check", "draft")
    assert story.act(draft_id, "export", "checked").json()["state"] == "exported"
    rows, _, text = word_parts(story.download(draft_id, ".docx")[1])

    assert rows[0] == ["Risk Description", "A Likelihood Rating", "B Impact Rating", "Overall Risk Score (A*B)",
                       "Description of proposed mitigation through the procurement process", "Risk Owner",
                       "Procurement Process Stage"]
    assert rows[1][1:4] == ["4", "3", "12"] and rows[1][6] == ""
    assert "set the risk owners and ratings." in text


def test_the_evidence_pack_records_who_set_each_owner_and_when(story):
    from pypdf import PdfReader

    exported(story)
    _, pack = story.download("draft-0001", ".pdf")
    # The PDF's text layer loses the space where a cell's words wrap, so the words are compared without spaces.
    text = "".join("".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(pack)).pages)

    assert "Fieldsyouset" in text
    fields = text.split("Fieldsyouset", 1)[1]
    assert fields.count("RiskOwnerImplementingagency,procurementAnaExample") == 2
