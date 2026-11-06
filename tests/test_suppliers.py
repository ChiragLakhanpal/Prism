"""Suppliers resolved on STEP supplier IDs first and names second (ticket 19), over the fixture (seam 1).

The gate builds data/out/fixture.duckdb with the nightly job's own run, so these tests read what the
run wrote: the awarded bidders it read from award notices, the candidate pairs name matching found
for rows without a STEP supplier ID, how each pair was routed, the suppliers gold holds and the
measures in strata.ops. A test that changes a threshold, a label or a decision runs on its own copy
of the database. Expected values come from tests/ground_truth/values.toml, where each one names its
recorded record, never from the code under test.
"""

import re
import shutil
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}


@pytest.fixture(scope="module")
def fixture(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql, **params):
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def bidders(engine, notice_id):
    return rows(engine, "SELECT position, name, step_supplier_id, country, individual_consultant "
                        "FROM strata.silver.notice_bidders WHERE notice_id = :notice_id ORDER BY position",
                notice_id=notice_id)


# ── Awarded bidders, read from award notices ─────────────────────────────

def test_an_award_notice_lists_each_awarded_bidder_with_the_step_supplier_id_it_carries(fixture):
    venture = TRUTH["awkward"]["joint_venture"]  # award notice OP00125855 lists both members
    first, second = VALUES["notice-bidder-503708"], VALUES["notice-bidder-503711"]

    found = bidders(fixture, venture["notice"])

    assert [(b["name"], b["step_supplier_id"], b["country"]) for b in found] == [
        (first["name"], first["value"], "Kenya"), (second["name"], second["value"], "Kenya")]
    assert [b["step_supplier_id"] for b in found] == venture["supplier_ids"]


def test_a_consultant_award_lists_each_firm_and_keeps_no_registry_id_or_score_as_a_bidder(fixture):
    # Award notice OP00192301 lists two firms, with a Registry ID line between them and the
    # evaluation scores after them. Neither line is a bidder.
    first, second = VALUES["notice-firm-636626"], VALUES["notice-firm-637051"]

    found = bidders(fixture, first["notice"])

    assert [(b["name"], b["step_supplier_id"]) for b in found] == [(first["name"], first["value"]),
                                                                   (second["name"], second["value"])]


def test_an_individual_consultant_awarded_in_a_notice_is_never_named(fixture):
    case = VALUES["notice-individual-consultant"]

    found = bidders(fixture, case["notice"])

    assert [(b["name"], b["step_supplier_id"], b["individual_consultant"]) for b in found] == [(None, None, True)]


def measures(engine, subject):
    return {row["measure"]: (row["count"], row["denominator"]) for row in rows(
        engine, "SELECT measure, count, denominator FROM strata.ops.data_readiness WHERE run_id = 'fixture' "
                "AND source = 'notices' AND subject = :subject "
                "AND measure IN ('awarded_bidder_id_on_award', 'awarded_bidder_id_same_name')", subject=subject)}


@pytest.mark.parametrize("subject", ["KE", "all"])  # every awarded bidder with an ID in the fixture is Kenya's
def test_strata_ops_counts_how_often_an_award_notice_carries_the_supplier_id_the_awards_give(fixture, subject):
    counted = TRUTH["counts"]["supplier_ids"]

    assert measures(fixture, subject) == {
        "awarded_bidder_id_on_award": (counted["agrees"], counted["on_award"]),
        "awarded_bidder_id_same_name": (counted["same_name_agrees"], counted["same_name"]),
    }


@pytest.mark.parametrize("firm", ["tradecon", "jedel", "geoscintex"])
def test_an_award_notice_can_give_a_firm_another_step_supplier_id_than_the_awards_give_it(fixture, firm):
    """The blueprint's "7 of 7" does not hold over every award notice: these three firms carry one ID in
    their award notice and another in the awards dataset, on the same STEP reference."""
    in_notice, in_awards = VALUES[f"supplier-id-{firm}-notice"], VALUES[f"supplier-id-{firm}-award"]

    bidder = rows(fixture, "SELECT b.name, b.step_supplier_id, n.step_reference FROM strata.silver.notice_bidders AS b "
                           "JOIN strata.gold.notice AS n ON n.notice_id = b.notice_id WHERE b.notice_id = :notice",
                  notice=in_notice["notice"])
    contract = rows(fixture, "SELECT c.step_reference, c.supplier_id, s.name FROM strata.gold.contract AS c "
                             "JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id WHERE c.contract_id = :id",
                    id=in_awards["contract"])

    assert bidder == [{"name": in_notice["name"], "step_supplier_id": in_notice["value"],
                       "step_reference": contract[0]["step_reference"]}]
    assert contract[0]["name"] == in_notice["name"] and contract[0]["supplier_id"] == in_awards["value"]


def test_an_awarded_bidder_written_without_an_id_keeps_its_name(fixture):
    case = VALUES["notice-bidder-no-id"]  # the FY2017-19 gap's award notice, OP00044090

    found = bidders(fixture, case["notice"])

    assert [(b["name"], b["step_supplier_id"], b["individual_consultant"]) for b in found] == [
        (case["value"], None, False)]


def test_an_awarded_bidder_written_with_a_personal_title_is_a_person_and_is_never_named():
    """No fixture notice writes a person this way, so the notice text is made up. The awards transform
    treats a supplier written with a personal title as a person (clean.titled), and so does the reader."""
    from strata.knowledge.suppliers.bidders import read

    [found] = read("Awarded Firm(s):\nDR. JANE DOE (123456)\nCountry: Kenya\n")

    assert (found.name, found.step_supplier_id, found.individual_consultant) == (None, "123456", True)


# ── Name matching, on plain rows ─────────────────────────────────────────
# The matching function takes plain rows and returns plain rows, so the nightly task calls it the
# same way on DuckDB and on Databricks (spec, "Data and the lakehouse run"). These rows are written
# by hand, because the fixture holds few rows without an ID.

def record(key, name, country, projects=("P000001",), has_id=False, group=None):
    from strata.knowledge.suppliers.matching import Record

    return Record(key=key, name=name, country=country, projects=tuple(projects), has_id=has_id,
                  group=group if group is not None or has_id else key.split("/")[0])


def match(*records):
    from strata.config import load_supplier_matching
    from strata.knowledge.suppliers.matching import candidate_pairs

    return candidate_pairs(list(records), load_supplier_matching(), floor=0.01)


def test_two_suppliers_with_step_supplier_ids_are_never_compared_by_name():
    """Two suppliers with IDs are never compared by name, however alike their names. Only the row with no
    ID is matched, and it may join either of them."""
    pairs = match(record("1001211", "CHINA INTERNATIONAL WATER AND ELECTRIC CORPORATION", "China", has_id=True),
                  record("534460", "China International Water & Electric Corporation", "China", has_id=True),
                  record("1513001/1", "CHINA INTERNATIONAL WATER & ELECTRIC CORP.", "China"))

    assert sorted((pair.left, pair.right) for pair in pairs) == [("1513001/1", "1001211"), ("1513001/1", "534460")]


def test_names_are_compared_without_legal_forms_accents_or_punctuation():
    pairs = match(record("1/1", "M/S Société Générale d'Études S.A.", "France"),
                  record("2/1", "SOCIETE GENERALE D ETUDES", "France"),
                  record("3/1", "ROAD & BRIDGE WORKS (K) PVT. LTD.", "Kenya"),
                  record("4/1", "Road and Bridge Works K Private Limited", "Kenya"))

    assert sorted((pair.left, pair.right, pair.name_level) for pair in pairs) == [
        ("1/1", "2/1", "same_name"), ("3/1", "4/1", "same_name")]


def test_rows_are_compared_only_within_one_country():
    assert match(record("1/1", "EGIS INTERNATIONAL", "France"), record("2/1", "EGIS INTERNATIONAL", "Kenya")) == []


def test_the_members_of_one_joint_venture_row_are_never_paired_with_each_other():
    pairs = match(record("1536431/1", "ECORYS NEDERLAND B.V.", "India"),
                  record("1536431/2", "ECORYS INDIA PVT. LTD.", "India"))

    assert pairs == []


def test_a_project_in_common_makes_the_same_name_likelier_to_be_one_supplier():
    shared = match(record("1/1", "LANDMARK HOLDINGS LIMITED", "Kenya", ["P124109"]),
                   record("2/1", "LANDMARK HOLDINGS LTD", "Kenya", ["P124109"]))
    apart = match(record("1/1", "LANDMARK HOLDINGS LIMITED", "Kenya", ["P124109"]),
                  record("2/1", "LANDMARK HOLDINGS LTD", "Kenya", ["P156634"]))

    assert shared[0].probability > apart[0].probability
    assert (shared[0].projects_level, apart[0].projects_level) == ("shared", "none_shared")


# ── Each supplier, resolved over the fixture ─────────────────────────────

def contract_supplier(engine, contract_id):
    found = rows(engine, "SELECT c.supplier_id, s.name, s.kind, s.resolved_on FROM strata.gold.contract AS c "
                         "LEFT JOIN strata.gold.supplier AS s ON s.supplier_id = c.supplier_id "
                         "WHERE c.contract_id = :contract_id", contract_id=contract_id)
    assert len(found) == 1, f"gold.contract holds {len(found)} rows for {contract_id}"
    return found[0]


def pair(engine, left_name, right_name):
    found = rows(engine, "SELECT * FROM strata.ops.supplier_pairs WHERE (left_name = :one AND right_name = :other) "
                         "OR (left_name = :other AND right_name = :one)", one=left_name, other=right_name)
    return found


def test_rows_with_no_step_supplier_id_named_alike_in_one_country_on_one_project_are_one_supplier(fixture):
    first, second = VALUES["fy2001-thales-1326397"], VALUES["fy2001-thales-1326726"]

    one, other = contract_supplier(fixture, first["contract"]), contract_supplier(fixture, second["contract"])

    assert one["supplier_id"] is not None and one["supplier_id"] == other["supplier_id"]
    assert (one["name"], one["kind"], one["resolved_on"]) == (first["value"], "firm", "name")
    [found] = [p for p in pair(fixture, first["value"], second["value"]) if p["left_key"].startswith(first["contract"])
               or p["right_key"].startswith(first["contract"])]
    assert (found["route"], found["outcome"], found["decided_by"]) == ("auto_merge", "merge", "threshold")


def test_no_row_with_a_step_supplier_id_enters_name_matching_over_the_fixture(fixture):
    """Criterion 2. A pair always has a row with no ID on its left (its key is a contract number or notice
    ID with its place), so two suppliers with IDs are never compared by name, and every row that writes an
    ID resolves to that ID. TRADECON (MSA) LTD keeps the ID its award notice gives, 987415, though the
    awards give the same name 987343: two IDs are never merged by name."""
    pairs = rows(fixture, "SELECT left_key, right_key FROM strata.ops.supplier_pairs")
    with_an_id = rows(fixture, "SELECT step_supplier_id, supplier_id, resolved_on FROM strata.silver.supplier_resolution "
                               "WHERE step_supplier_id IS NOT NULL")
    tradecon = VALUES["supplier-id-tradecon-notice"]

    assert pairs and all("/" in pair["left_key"] for pair in pairs)
    assert with_an_id and all((row["supplier_id"], row["resolved_on"]) == (row["step_supplier_id"], "step_supplier_id")
                              for row in with_an_id)
    assert contract_supplier(fixture, VALUES["supplier-id-tradecon-award"]["contract"])["supplier_id"] == \
        VALUES["supplier-id-tradecon-award"]["value"]
    assert rows(fixture, "SELECT supplier_id FROM strata.silver.supplier_resolution WHERE source_key = :notice",
                notice=tradecon["notice"]) == [{"supplier_id": tradecon["value"]}]


def routed(engine, left_contains, right_contains):
    found = rows(engine, "SELECT * FROM strata.ops.supplier_pairs WHERE left_name = :left AND right_name = :right",
                 left=left_contains, right=right_contains)
    assert len(found) >= 1, f"no pair of {left_contains} and {right_contains}"
    return found


def test_a_pair_in_the_uncertain_middle_goes_to_the_model_whose_merge_stands_when_it_is_sure(fixture):
    """The FY2001 to FY2016 row for CHINA RAILWAY NO. 10 ENGINEERING GROUP shares no project with supplier
    426408, written China Railway No.10 Engineering Group Co., Ltd., so Splink is not sure enough to merge
    them, and the model decides. The offline stand-in merges names that are the same once normalized."""
    old, award = VALUES["fy2001-china-railway"], VALUES["award-china-railway-426408"]

    [found] = routed(fixture, old["value"], award["name"])

    assert (found["route"], found["decided_by"], found["outcome"]) == ("model", "model", "merge")
    assert found["model_decision"] == "merge" and found["model"].startswith("offline stand-in")
    assert contract_supplier(fixture, old["contract"])["supplier_id"] == award["value"]


def test_a_pair_the_model_is_not_sure_of_waits_for_a_person(fixture):
    """INTERCONTINENTAL CONSULTANTS & TEC is cut off at 40 characters; INTERCONTINENTAL CONSULTANTS AND TECH
    may be the same firm. The stand-in is not sure, so a person decides."""
    cut_off, longer = VALUES["fy2001-intercontinental-cut-off"], VALUES["fy2001-intercontinental-and-tech"]

    found = routed(fixture, cut_off["value"], longer["value"])

    assert {(p["route"], p["review_reason"], p["outcome"], p["model_decision"]) for p in found} == {
        ("person", "model_unsure", "waiting", "unsure")}


def test_a_name_that_matches_two_step_supplier_ids_waits_for_a_person(fixture):
    """Award notice OP00054114 writes LOSAI MANAGEMENT LIMITED with no ID. The same name carries 391987 in
    other notices, and LOSAI MANAGEMENT LTD. carries 477806 in the awards. Merging the row with both would
    join two IDs by name, so both pairs wait for a person and the row stays a supplier of its own."""
    row, one_id, other_id = VALUES["notice-losai-no-id"], VALUES["notice-losai-391987"], VALUES["award-losai-477806"]

    found = rows(fixture, "SELECT right_key, route, review_reason, outcome FROM strata.ops.supplier_pairs "
                          "WHERE left_name = :name AND left_key LIKE :notice ORDER BY right_key",
                 name=row["value"], notice=f"{row['notice']}/%")
    resolved = rows(fixture, "SELECT supplier_id, resolved_on FROM strata.silver.supplier_resolution "
                             "WHERE source_key = :notice AND name = :name", notice=row["notice"], name=row["value"])

    assert found == [{"right_key": key, "route": "person", "review_reason": "two_step_supplier_ids", "outcome": "waiting"}
                     for key in sorted([one_id["value"], other_id["value"]])]
    assert resolved[0]["supplier_id"].startswith("N-") and resolved[0]["resolved_on"] == "unmatched"


# ── Routing by the thresholds file ───────────────────────────────────────

@pytest.fixture
def writable(fixture_db, tmp_path):
    """A writable copy of the fixture database, for a test that runs resolution again."""
    target = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, target)
    with DuckDBEngine.open(target) as engine:
        yield engine


def thresholds_with(tmp_path, **changed):
    from strata.config import load_thresholds

    text = (ROOT / "config" / "thresholds.toml").read_text()
    for name, value in changed.items():
        line = next(line for line in text.splitlines() if line.startswith(f"{name} = "))
        text = text.replace(line, f"{name} = {value}")
    path = tmp_path / "thresholds.toml"
    path.write_text(text)
    return load_thresholds(path)


def resolve_again(engine, thresholds=None, judge=None):
    from strata.knowledge.suppliers import resolve
    from strata.knowledge.suppliers.judge import SameNameStandIn
    from strata.lakehouse import gold

    resolve.run(engine, "again", judge or SameNameStandIn(), thresholds=thresholds)
    gold.build(engine)


@pytest.mark.parametrize(("changed", "route", "decided_by"), [
    ({"auto_merge_min_probability": 0.8}, "auto_merge", "threshold"),
    ({"model_min_probability": 0.9, "auto_merge_min_probability": 0.99}, "kept_apart", "threshold"),
])
def test_changing_a_threshold_changes_the_routing_of_a_fixture_pair(writable, tmp_path, changed, route, decided_by):
    """Criterion 3. The CHINA RAILWAY pair goes to the model with the thresholds file as it is. Lowering
    auto_merge_min_probability merges it with no model; raising model_min_probability keeps it apart, and
    contract 1519849 is then signed by a supplier known only by name."""
    old, award = VALUES["fy2001-china-railway"], VALUES["award-china-railway-426408"]

    resolve_again(writable, thresholds_with(tmp_path, **changed))

    [found] = routed(writable, old["value"], award["name"])
    assert (found["route"], found["decided_by"]) == (route, decided_by)
    supplier = contract_supplier(writable, old["contract"])["supplier_id"]
    assert supplier == award["value"] if route == "auto_merge" else supplier.startswith("N-")


class FailingJudge:
    """A judge that cannot answer, as when Azure OpenAI times out or answers in the wrong shape."""

    name = "failing judge"

    def decide(self, questions):
        from strata.knowledge.suppliers.judge import JudgeError

        raise JudgeError("Azure OpenAI did not answer in 60 seconds.")


def test_a_judge_that_cannot_answer_leaves_the_middle_to_a_person_and_the_run_goes_on(writable, caplog):
    """One failed call to the model must not stop the night's gold build. The CHINA RAILWAY pair, which
    the model decides when it answers, waits for a person instead."""
    old, award = VALUES["fy2001-china-railway"], VALUES["award-china-railway-426408"]

    resolve_again(writable, judge=FailingJudge())

    [found] = routed(writable, old["value"], award["name"])
    assert (found["route"], found["review_reason"], found["outcome"], found["model"]) == (
        "person", "no_model", "waiting", None)
    assert "failing judge could not answer" in caplog.text


def test_a_judge_that_fails_keeps_the_judgements_it_gave_on_earlier_nights_and_only_new_pairs_wait(writable, caplog):
    """Ticket 19's review, P1. One timeout from Azure OpenAI must not undo every merge the model made: the run keeps
    each earlier judgement whose judge and names are the same, and only a pair it would ask about now waits for a
    person. One INTERCONTINENTAL pair has no earlier judgement here, so it is the new question."""
    from strata.knowledge.suppliers.judge import SameNameStandIn

    old, award = VALUES["fy2001-china-railway"], VALUES["award-china-railway-426408"]
    writable.run("UPDATE strata.ops.supplier_pairs SET model_decision = NULL WHERE pair_id = :pair",
                 {"pair": "1527581/1|1541213/1"})
    failing = FailingJudge()
    failing.name = SameNameStandIn.name

    resolve_again(writable, judge=failing)

    [kept] = routed(writable, old["value"], award["name"])
    assert (kept["route"], kept["decided_by"], kept["outcome"]) == ("model", "model", "merge")
    assert contract_supplier(writable, old["contract"])["supplier_id"] == award["value"]
    [asked] = rows(writable, "SELECT route, review_reason, outcome FROM strata.ops.supplier_pairs WHERE pair_id = :pair",
                   pair="1527581/1|1541213/1")
    assert (asked["route"], asked["review_reason"], asked["outcome"]) == ("person", "no_model", "waiting")
    assert "kept its earlier judgements" in caplog.text


def test_a_name_only_supplier_is_named_by_a_row_public_on_the_day_the_supplier_became_public():
    """Ticket 19's verify, O2. A supplier known only by name is public from its earliest row, so its name is the
    longest way the rows public that day write it, never a longer name a later row brought: a query as of the earlier
    day must not show a name that was not public yet. Made-up rows."""
    import datetime as dt

    from strata.knowledge.suppliers.resolve import RESOLUTION_COLUMNS
    from strata.lakehouse import catalog, gold

    def resolved(key, name, day):
        return ("hand", "awards_fy2001_2016", key, 1, key, "P000001", name, "Kenya", None, False, "N-000000000001",
                None, "name", day)

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        engine.insert_rows("strata.silver.supplier_resolution", RESOLUTION_COLUMNS, [
            resolved("1500001", "EGIS INTL", dt.date(2015, 1, 1)),
            resolved("1500002", "EGIS INTERNATIONAL SA", dt.date(2018, 1, 1))])
        gold.sync(engine, "supplier")
        found = rows(engine, "SELECT name, public_from FROM strata.gold.supplier WHERE supplier_id = 'N-000000000001'")

    assert found == [{"name": "EGIS INTL", "public_from": dt.date(2015, 1, 1)}]


def test_a_persons_no_merge_keeps_two_rows_apart_whatever_other_merges_link_them(writable):
    """Ticket 19's verify, V1. The fixture's five EGIS INTERNATIONAL rows with no STEP supplier ID are merged pair by
    pair. A person says 1500446/1 and 1517730/1 are not one firm. The other merges still link them, so every merge in
    their group goes to a person (person_kept_apart), and the two rows resolve to two suppliers."""
    from strata.server.suppliers import SupplierLog

    SupplierLog(lambda: writable.cursor()).decide("1500446/1|1517730/1", "no_merge", "4021@1984",
                                                  "Two offices with their own registrations.")
    resolve_again(writable)

    pairs = rows(writable, "SELECT pair_id, route, outcome, decided_by, review_reason FROM strata.ops.supplier_pairs "
                           "WHERE left_name = 'EGIS INTERNATIONAL' ORDER BY pair_id")
    suppliers = {row["source_key"]: row["supplier_id"] for row in rows(
        writable, "SELECT source_key, supplier_id FROM strata.silver.supplier_resolution "
                  "WHERE source_key IN ('1500446', '1517730')")}

    [said] = [pair for pair in pairs if pair["pair_id"] == "1500446/1|1517730/1"]
    assert (said["outcome"], said["decided_by"]) == ("no_merge", "person")
    others = [pair for pair in pairs if pair["pair_id"] != "1500446/1|1517730/1"]
    assert others and {(pair["route"], pair["outcome"], pair["review_reason"]) for pair in others} == {
        ("person", "waiting", "person_kept_apart")}
    assert suppliers["1500446"] != suppliers["1517730"]


# ── Routing, on plain rows written by hand ───────────────────────────────

def supplier_row(source_key, name, country="Kenya", project="P000001", supplier_id=None, source="awards_fy2001_2016",
                 position=1):
    import datetime as dt

    from strata.knowledge.suppliers.resolve import SupplierRow

    return SupplierRow(source, source_key, position, source_key, project, name, country, supplier_id, False, source_key,
                       dt.date(2015, 1, 1))


class CountingJudge:
    """A judge that merges every pair, sure of it, and counts what it was asked."""

    name = "test judge"

    def __init__(self, decision="merge", confidence=0.99):
        self.asked, self.decision, self.confidence = [], decision, confidence

    def decide(self, questions):
        from strata.knowledge.suppliers.judge import Judgement

        self.asked += questions
        return [Judgement(self.decision, self.confidence, "the test said so") for _ in questions]


def resolved_by_hand(rows_, judge=None, decisions=None, past=None, **changed):
    from strata.config import load_supplier_matching, load_thresholds
    from strata.knowledge.suppliers.resolve import Routing, resolve

    routing = Routing.from_thresholds(load_thresholds())
    routing = type(routing)(**{**routing.__dict__, **changed})
    return resolve(rows_, routing, load_supplier_matching(), judge, decisions, past)


# The same firm on two projects: Splink is not sure enough to merge with no model (probability 0.80).
APART = [supplier_row("1500001", "MWANGI WATER WORKS LTD", project="P000001"),
         supplier_row("1500002", "MWANGI WATER WORKS LIMITED", project="P000002")]


def test_with_no_model_a_pair_in_the_middle_waits_for_a_person():
    [found] = resolved_by_hand(APART, judge=None).pairs

    assert (found.route, found.review_reason, found.outcome) == ("person", "no_model", "waiting")


def test_a_judgement_an_earlier_run_kept_is_not_asked_again_while_the_judge_and_names_are_the_same():
    from strata.knowledge.suppliers.judge import Judgement
    from strata.knowledge.suppliers.resolve import PastJudgement

    judge = CountingJudge()
    kept = {"1500001/1|1500002/1": PastJudgement("test judge", "MWANGI WATER WORKS LTD", "MWANGI WATER WORKS LIMITED",
                                                 Judgement("no_merge", 0.97, "an earlier answer"))}

    [found] = resolved_by_hand(APART, judge=judge, past=kept).pairs

    assert judge.asked == [] and (found.outcome, found.decided_by) == ("no_merge", "model")


def test_the_model_is_asked_about_at_most_model_pairs_per_run_new_pairs_and_the_rest_wait_for_a_person():
    """config/thresholds.toml's model_pairs_per_run caps one night's calls to the model, the pairs Splink
    is surer of first. A name cut off at 40 characters, on the same project, scores about 0.85; the
    MWANGI pair, on two projects, about 0.80. With a limit of 1, the model is asked about the first,
    and the MWANGI pair waits for a person until a later night."""
    cut_off = [supplier_row("1500003", "OTIENO ROADS AND BRIDGES CONSTRUCTION", project="P000003"),
               supplier_row("1500004", "OTIENO ROADS AND BRIDGES CONSTR", project="P000003")]
    judge = CountingJudge()

    pairs = resolved_by_hand(APART + cut_off, judge=judge, model_pairs_per_run=1).pairs

    [asked] = judge.asked
    assert {asked.left.name, asked.right.name} == {"OTIENO ROADS AND BRIDGES CONSTRUCTION",
                                                   "OTIENO ROADS AND BRIDGES CONSTR"}
    by_name = {pair.left.name: pair for pair in pairs}
    mwangi = next(pair for name, pair in by_name.items() if name.startswith("MWANGI"))
    otieno = next(pair for name, pair in by_name.items() if name.startswith("OTIENO"))
    assert (otieno.route, otieno.decided_by, otieno.outcome) == ("model", "model", "merge")
    assert (mwangi.route, mwangi.review_reason, mwangi.outcome) == ("person", "no_model", "waiting")


def test_a_model_decision_below_the_confidence_threshold_goes_to_a_person():
    [found] = resolved_by_hand(APART, judge=CountingJudge(confidence=0.6)).pairs

    assert (found.route, found.review_reason) == ("person", "model_unsure")


def test_a_persons_decision_outranks_the_thresholds_and_the_model():
    from strata.knowledge.suppliers.resolve import Decision

    no = {"1500001/1|1500002/1": Decision("no_merge", "4021@1984", "Different directors, per the notices.",
                                          "MWANGI WATER WORKS LTD", "MWANGI WATER WORKS LIMITED")}

    resolution = resolved_by_hand(APART, judge=CountingJudge(), decisions=no)

    [found] = resolution.pairs
    assert (found.outcome, found.decided_by, found.reviewer, found.decision_reason) == (
        "no_merge", "person", "4021@1984", "Different directors, per the notices.")
    assert len({row.supplier_id for row in resolution.rows}) == 2


def test_a_persons_decision_is_not_applied_once_the_pair_names_another_firm():
    """A pair is keyed by row positions. When a revised notice lists its bidders in a new order, the same
    key names another firm, so a decision stands only while both names are the ones the person saw."""
    from strata.knowledge.suppliers.resolve import Decision

    seen = {"1500001/1|1500002/1": Decision("no_merge", "4021@1984", "Different directors, per the notices.",
                                            "KAMAU WATER WORKS LTD", "MWANGI WATER WORKS LIMITED")}

    [found] = resolved_by_hand(APART, judge=CountingJudge(), decisions=seen).pairs

    assert (found.outcome, found.decided_by, found.reviewer) == ("merge", "model", None)


# ── Labels and the auto-merge precision on them ──────────────────────────

def quality(engine, run_id="fixture"):
    [found] = rows(engine, "SELECT * FROM strata.ops.supplier_match_quality WHERE run_id = :run_id", run_id=run_id)
    return found


def test_with_no_pair_labeled_strata_ops_reports_counts_and_no_precision(fixture):
    found = quality(fixture)
    candidate = rows(fixture, "SELECT count(*) AS n FROM strata.ops.supplier_pairs")[0]["n"]

    assert (found["candidate_pairs"], found["labeled_pairs"], found["labeled_pairs_target"]) == (candidate, 0, 1000)
    assert (found["auto_merge_precision"], found["interval_low"], found["interval_high"],
            found["lowest_threshold_meeting_target"]) == (None, None, None, None)
    assert (found["precision_target"], found["auto_merge_min_probability"]) == (0.98, 0.99)


def label_all(engine, wrong=0, also=()):
    """Label every auto-merged pair merge, except the first `wrong` of them, and each pair in also no_merge,
    through the labeling tool's own writer."""
    from strata.server.suppliers import SupplierLog

    log = SupplierLog(lambda: engine)
    merged = [row["pair_id"] for row in rows(engine, "SELECT pair_id FROM strata.ops.supplier_pairs "
                                                     "WHERE route = 'auto_merge' ORDER BY pair_id")]
    for number, pair_id in enumerate(merged):
        log.label(pair_id, "no_merge" if number < wrong else "merge", "4021@1984")
    for pair_id in also:
        log.label(pair_id, "no_merge", "4021@1984")
    return merged


# The 95% Wilson score intervals below were computed apart from Prism's code on October 24, 2026, with
# statsmodels 0.14.4: proportion_confint(k, n, alpha=0.05, method="wilson").
WILSON = {(29, 30): (0.8332960900859081, 0.9940914096183875), (30, 30): (0.8864866068260311, 1.0)}


class Unclosed:
    """The writable engine, which SupplierLog must not close between labels."""

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def close(self):
        pass


def test_strata_ops_reports_the_auto_merge_precision_on_the_labeled_pairs_with_its_interval(writable):
    from strata.knowledge.suppliers import quality as supplier_quality

    merged = label_all(Unclosed(writable), wrong=1)
    supplier_quality.measure(writable, "labeled")

    found = quality(writable, "labeled")
    assert (found["labeled_pairs"], found["labeled_auto_merged"], found["labeled_auto_merged_right"]) == (
        len(merged), len(merged), len(merged) - 1)
    assert len(merged) == 30  # the fixture's auto-merged pairs, which WILSON's literals were computed for
    assert found["auto_merge_precision"] == pytest.approx(29 / 30)
    assert (found["interval_low"], found["interval_high"]) == pytest.approx(WILSON[(29, 30)], abs=1e-6)
    assert found["lowest_threshold_meeting_target"] is None  # 29 of 30 falls short of 0.98 at every probability


def test_a_label_joins_only_the_pair_whose_two_names_it_was_given(writable):
    """Ticket 19's review, P2. A pair is keyed by row positions, so a revised notice that lists its bidders in a new
    order gives an old key to another firm. A label keeps the two names it was given and joins a pair only while
    the pair still has them: a label whose left name differs is not counted, and the pair is offered again."""
    import datetime as dt

    from strata.knowledge.suppliers import quality as supplier_quality
    from strata.server.suppliers import SupplierLog, labeling_list

    [first, second] = rows(writable, "SELECT pair_id, left_key, right_key, right_name FROM strata.ops.supplier_pairs "
                                     "WHERE route = 'auto_merge' ORDER BY pair_id LIMIT 2")
    SupplierLog(lambda: Unclosed(writable)).label(first["pair_id"], "merge", "4021@1984")
    writable.insert_rows("strata.ops.supplier_pair_labels", ("pair_id", "left_key", "right_key", "left_name",
                                                             "right_name", "label", "labeler", "labeled_at",
                                                             "public_from"),
                         [(second["pair_id"], second["left_key"], second["right_key"], "ANOTHER FIRM LTD",
                           second["right_name"], "merge", "4021@1984", dt.datetime(2026, 10, 24, tzinfo=dt.UTC),
                           dt.date(2026, 10, 24))])
    supplier_quality.measure(writable, "labeled")

    offered = {pair["pair_id"] for pair in labeling_list(writable, 100, 1000)["pairs"]}
    assert labeling_list(writable, 100, 1000)["labeled_pairs"] == 1
    assert quality(writable, "labeled")["labeled_pairs"] == 1
    assert second["pair_id"] in offered and first["pair_id"] not in offered
    [kept] = rows(writable, "SELECT left_name, right_name FROM strata.ops.supplier_pair_labels WHERE pair_id = :pair",
                  pair=first["pair_id"])
    assert kept["left_name"] and kept["right_name"]


def test_the_lowest_threshold_at_which_labeled_pairs_reach_0_98_is_reported(writable):
    """With every auto-merged pair labeled merge and the model's CHINA RAILWAY pair (0.80) labeled no_merge,
    precision is 30 of 30 at the auto-merged pairs' probability and 30 of 31 below it, so that probability
    is the lowest threshold that keeps auto-merge at 0.98 or more on the labels."""
    from strata.knowledge.suppliers import quality as supplier_quality

    [china] = rows(writable, "SELECT pair_id FROM strata.ops.supplier_pairs WHERE route = 'model'")
    merged = label_all(Unclosed(writable), also=[china["pair_id"]])
    supplier_quality.measure(writable, "labeled")

    found = quality(writable, "labeled")
    [probability] = {row["match_probability"] for row in rows(
        writable, "SELECT match_probability FROM strata.ops.supplier_pairs WHERE route = 'auto_merge'")}
    assert (found["labeled_pairs"], found["auto_merge_precision"]) == (len(merged) + 1, 1.0)
    assert (found["interval_low"], found["interval_high"]) == pytest.approx(WILSON[(30, 30)], abs=1e-6)
    assert found["lowest_threshold_meeting_target"] == pytest.approx(probability)
    assert found["lowest_threshold_meeting_target"] >= found["auto_merge_min_probability"]


def test_below_twenty_labeled_auto_merged_pairs_there_is_no_precision_and_no_interval(writable):
    from strata.knowledge.suppliers import quality as supplier_quality
    from strata.server.suppliers import SupplierLog

    log = SupplierLog(lambda: Unclosed(writable))
    for row in rows(writable, "SELECT pair_id FROM strata.ops.supplier_pairs WHERE route = 'auto_merge' "
                              "ORDER BY pair_id LIMIT 19"):
        log.label(row["pair_id"], "merge", "4021@1984")
    supplier_quality.measure(writable, "nineteen")

    found = quality(writable, "nineteen")
    assert (found["labeled_auto_merged"], found["auto_merge_precision"], found["interval_low"]) == (19, None, None)


# ── Joint ventures ───────────────────────────────────────────────────────

def test_the_fixtures_joint_venture_is_one_supplier_linked_to_its_members(fixture):
    """Criterion 6. values.toml, awkward.joint_venture: contract 1624689 went to 503708 and 503711 together,
    and award notice OP00125855 lists both. Both sources give the same supplier, JV-503708-503711, which
    gold.contract_supplier links to its two members."""
    venture = TRUTH["awkward"]["joint_venture"]
    key = "JV-" + "-".join(venture["supplier_ids"])
    first, second = VALUES["notice-bidder-503708"], VALUES["notice-bidder-503711"]

    supplier = rows(fixture, "SELECT supplier_id, name, kind, member_count, resolved_on FROM strata.gold.supplier "
                             "WHERE supplier_id LIKE 'JV-%' AND (supplier_id LIKE :one OR supplier_id LIKE :other)",
                    one=f"%{venture['supplier_ids'][0]}%", other=f"%{venture['supplier_ids'][1]}%")
    members = rows(fixture, "SELECT supplier_id, joint_venture_id FROM strata.gold.contract_supplier "
                            "WHERE contract_id = :contract ORDER BY supplier_id", contract=venture["contract"])
    from_notice = rows(fixture, "SELECT DISTINCT joint_venture_id FROM strata.silver.supplier_resolution "
                                "WHERE source_key = :notice", notice=venture["notice"])

    assert supplier == [{"supplier_id": key, "name": f"{second['name']} / {first['name']}", "kind": "joint venture",
                         "member_count": 2, "resolved_on": "step_supplier_id"}]
    assert members == [{"supplier_id": member, "joint_venture_id": key} for member in venture["supplier_ids"]]
    assert contract_supplier(fixture, venture["contract"])["supplier_id"] == key
    assert from_notice == [{"joint_venture_id": key}]


def test_a_fy2001_2016_row_that_names_a_joint_venture_is_its_own_supplier_linked_to_each_member(fixture):
    row = VALUES["fy2001-joint-venture-row"]

    venture = contract_supplier(fixture, row["contract"])
    members = rows(fixture, "SELECT s.name, cs.joint_venture_id FROM strata.gold.contract_supplier AS cs "
                            "JOIN strata.gold.supplier AS s ON s.supplier_id = cs.supplier_id "
                            "WHERE cs.contract_id = :contract ORDER BY s.name", contract=row["contract"])

    assert (venture["kind"], venture["supplier_id"].startswith("JV-")) == ("joint venture", True)
    assert venture["name"] == " / ".join(sorted(row["members"]))
    assert members == [{"name": name, "joint_venture_id": venture["supplier_id"]} for name in sorted(row["members"])]


# ── No score, rank, rating or profile ────────────────────────────────────

def test_the_supplier_tables_expose_no_score_rank_or_rating_column(fixture):
    """Criterion 7. Every table and view whose name holds supplier, in every schema."""
    columns = rows(fixture, "SELECT table_schema, table_name, column_name FROM system.information_schema.columns "
                            "WHERE table_catalog = 'strata' AND table_name LIKE '%supplier%'")
    tables = {f"{column['table_schema']}.{column['table_name']}" for column in columns}

    assert {"gold.supplier", "gold.contract_supplier", "silver.supplier_resolution", "ops.supplier_pairs",
            "ops.supplier_review_list", "ops.supplier_match_quality"} <= tables
    assert [f"{c['table_schema']}.{c['table_name']}.{c['column_name']}" for c in columns
            if re.search(r"score|rank|rating|grade|performance", c["column_name"])] == []


def test_no_tool_in_the_registry_returns_a_supplier_profile():
    """Criterion 7, through the tool registry (config/tools.toml), which generates the agent's tool list. A
    supplier profile would take a supplier and return what Prism holds about it: no tool takes a supplier
    as a parameter, and no tool's row is a supplier or carries a field about one."""
    from strata.config import load_tools
    from strata.tools.registry import agent_tools

    tools = load_tools()
    # research_evidence's sanctions check states two counts over all of a project's suppliers (ticket 154), which say
    # nothing about any one supplier.
    counts = {"suppliers_checked", "suppliers_sanctioned"}

    for tool in tools.values():
        assert not [p.name for p in tool.parameters if "supplier" in f"{p.name} {p.description}".lower()], tool.name
        assert "supplier" not in tool.result.row.lower(), tool.name
        assert not [f for f in tool.result.row_fields + tool.result.fields if "supplier" in f and f not in counts], \
            tool.name
    assert [tool["name"] for tool in agent_tools(tools)] == list(tools)


def test_the_live_judge_check_asks_about_the_fixtures_uncertain_pairs_and_writes_nothing(fixture_db, tmp_path,
                                                                                        monkeypatch, capsys):
    """ops/suppliers/judge_live.py, the workspace step that proves the live judge, run here with Azure
    OpenAI's answer in its documented shape (tests/fixtures/azure/supplier_judge.json) in place of the call."""
    import importlib.util
    import json

    from strata.knowledge.suppliers import judge

    spec = importlib.util.spec_from_file_location("judge_live", ROOT / "ops" / "suppliers" / "judge_live.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    answer = json.loads((ROOT / "tests" / "fixtures" / "azure" / "supplier_judge.json").read_text())["response"]
    asked = []
    monkeypatch.setattr(judge, "http_post", lambda url, headers, body: asked.append(body) or answer)
    monkeypatch.setattr(script, "FIXTURE_DB", fixture_db)
    keys = tmp_path / "azure-keys.txt"
    keys.write_text("AZURE_OPENAI_ENDPOINT='https://wb-strata.openai.azure.com/openai/v1'\n"
                    "AZURE_OPENAI_API_KEY='not-a-real-key'\n")

    assert script.main(["--env-file", str(keys)]) == 0
    printed = capsys.readouterr().out
    # The thresholds send three fixture pairs to the model: CHINA RAILWAY and the two INTERCONTINENTAL pairs.
    assert len(asked) == 3 and VALUES["fy2001-china-railway"]["value"] in printed


def test_the_nightly_jobs_serverless_environment_installs_the_splink_that_pyproject_pins():
    """bronze_to_gold runs name matching with Splink on serverless compute, which installs only what the
    job's environment lists, so the job lists the same pin as pyproject.toml."""
    from strata.lakehouse import bundle

    pinned = next(dependency for dependency in tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "dependencies"] if dependency.startswith("splink"))
    [environment] = bundle.load().resources("jobs")["nightly"]["environments"]

    assert pinned in environment["spec"].get("dependencies", [])


def test_the_nightly_jobs_environment_installs_the_pypdf_and_pyyaml_the_live_readers_pin():
    """parse_and_embed reads each PDF's pages and cuts Route B's pages with pypdf, and every task reads the bundle's
    YAML for its night and window, so the job lists the pins the live readers' scripts run with (review B5)."""
    import re

    from strata.lakehouse import bundle

    [environment] = bundle.load().resources("jobs")["nightly"]["environments"]
    for script in ("ops/plans/run_live.py", "ops/documents/run_live.py"):
        header = (ROOT / script).read_text().split("# ///")[1]
        for name in ("pypdf", "pyyaml"):
            assert re.search(rf'"({name}==[^"]+)"', header).group(1) in environment["spec"]["dependencies"]
    # The document run checks passages' languages with py3langid (ticket 42), at pyproject.toml's pin.
    documents = (ROOT / "ops/documents/run_live.py").read_text().split("# ///")[1]
    pinned = re.search(r'"(py3langid==[^"]+)"', (ROOT / "pyproject.toml").read_text()).group(1)
    assert pinned in documents and pinned in environment["spec"]["dependencies"]
