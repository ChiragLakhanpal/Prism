"""Planning a package from a sentence, at seam 3 (ticket 15).

POST /api/planned-packages streams the plan-a-package workflow: the package reader (the drafting model, one
structured call, replayed here from tests/fixtures/agent/packages.toml) reads the sentence into the package
form schema's fields, review type and market approach are computed from the thresholds file, the package
is saved in the app state store (Lakebase on the App, ADR 0005; a DuckDB file here) for the person who made it,
and find_comparables runs on the criteria that pick the
comparables. GET and POST /api/planned-packages/{id} read and change a saved package; GET
/api/planned-packages lists the viewer's packages and the plans they checked, for the Packages tab.

Expected values come from independent sources: the chips the ticket's first acceptance criterion lists
(the blueprint's Package workspace wireframe), the thresholds the blueprint states ("works of US$10 million
or more go to prior review, and this country's plans send works of US$15 million or more to international
bidding"), and the comparables ticket 12 recorded for Kenya's works under Request for Bids.
"""

import asyncio
import datetime as dt
import json
import shutil
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.agent.loop import AgentError
from strata.agent.runs import RunLog
from strata.agent.scripted import PACKAGE_CASES, ScriptedAgent, load_cases
from strata import appstate
from strata.config import load_package_form, load_thresholds
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine
from strata.packages.store import PackageStore
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
TODAY = dt.date(2026, 10, 23)
SENTENCE = "rural roads, Kenya, about US$15 million"


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"40{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN = viewer(21, "Ana"), viewer(22, "Ben")


class Clock:
    def __init__(self, start: dt.datetime):
        self.at = start

    def __call__(self) -> dt.datetime:
        return self.at

    def move(self, **delta):
        self.at += dt.timedelta(**delta)


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


def events(text: str) -> list[tuple[str, dict]]:
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


@pytest.fixture(scope="module")
def empty_ops(tmp_path_factory):
    """strata.ops with the catalog's tables and no rows, for the run log, built once: making every table takes
    about a second."""
    path = tmp_path_factory.mktemp("ops") / "empty.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def state_db(tmp_path):
    """The app state store with only its own tables (src/strata/appstate), as Lakebase holds them on the App:
    no strata.ops table is there, so a package written anywhere else fails."""
    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        appstate.build(engine)
    return path


@pytest.fixture
def ops_db(tmp_path, empty_ops):
    path = tmp_path / "ops.duckdb"
    shutil.copyfile(empty_ops, path)
    return path


@pytest.fixture
def clock():
    return Clock(dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC))


@pytest.fixture
def planning(fixture_db, state_db, ops_db, clock):
    """The app with the fixture database, app state in a DuckDB file, runs in strata.ops in another, and the
    scripted package reader."""
    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    def ops():
        return DuckDBEngine.open(ops_db)

    def make(case: str = "package-rural-roads-kenya", reader=None, thresholds=None, form=None, engine_for=None):
        cases = load_cases(PACKAGE_CASES)
        numbers = iter(range(1, 100))
        return create_app(engine_for=engine_for or reading, packages=PackageStore(state), runs=RunLog(ops),
                          package_reader=reader or (lambda: ScriptedAgent(cases[case])),
                          package_thresholds=thresholds, package_form=form, today=lambda: TODAY, now=clock,
                          new_package_id=lambda: f"pkg-{next(numbers):012d}", new_run_id=lambda: "run-0001")
    return make


def plan(app, sentence=SENTENCE, headers=ANA, **extra) -> tuple[list, dict | None]:
    sent = events(call(app, "POST", "/api/planned-packages", headers, json={"sentence": sentence, **extra}).text)
    made = [data for kind, data in sent if kind == "package"]
    return sent, made[0]["package"] if made else None


def chips(package: dict) -> dict[str, list[tuple[str, object, str]]]:
    """Each group's chips with a value, as (field, value, provenance), in the schema's order."""
    grouped: dict[str, list] = {}
    for field in package["fields"]:
        if field["value"] is not None:
            grouped.setdefault(field["group"], []).append((field["key"], field["value"], field["provenance"]))
    return grouped


def test_the_screens_recorded_package_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_packages_api.py writes the answers the package screens' tests serve, from one story on the
    fixture; the routes must still answer with them word for word."""
    from record_packages_api import answers

    for name, text in answers(tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), f"{name} is out of date"


# ── Reading a sentence ──────────────────────────────────────────────────

def test_the_sentence_yields_the_wireframe_s_chips_with_two_computed_and_one_guess(planning):
    _, package = plan(planning())

    assert chips(package) == {
        "what": [("category", "Works", "sentence"), ("description", "Rural roads", "sentence"),
                 ("estimated_amount_usd", 15_000_000, "sentence"), ("lots", 2, "guess")],
        "where": [("country", "KE", "sentence")],
        "how": [("method", "Request for Bids", "default"), ("market_approach", "Open - International", "computed"),
                ("procurement_process", "Single Stage - One Envelope", "default"),
                ("prequalification", "No", "default"), ("review_type", "Prior", "computed")],
    }
    assert package["guesses"] == 1
    assert package["sentence"] == SENTENCE


def test_the_computed_note_reads_its_rules_and_its_source_from_the_thresholds_file(planning):
    _, package = plan(planning())

    review, market = package["rules"]["review"], package["rules"]["market_approach"]
    assert (review["category"], review["threshold_usd"], review["risk_rating"]) == ("Works", 10_000_000, "High")
    assert (market["country"], market["category"], market["threshold_usd"]) == ("KE", "Works", 15_000_000)
    file = load_thresholds()
    assert review["source"] == file.value("review.source")
    assert market["source"] == file.value("market_approach.source")
    # The values are the blueprint's, not yet checked against the World Bank's tables, so the file gives no date
    # and the note claims none (review round 2, P4).
    assert (review["as_of"], market["as_of"]) == (None, None)


def test_raising_the_prior_review_threshold_in_the_file_makes_the_review_type_chip_post_with_no_code_change(planning, tmp_path):
    text = (ROOT / "config" / "thresholds.toml").read_text()
    raised = tmp_path / "thresholds.toml"
    raised.write_text(text.replace("[review.prior_from_usd.High]\nWorks = 10_000_000",
                                   "[review.prior_from_usd.High]\nWorks = 20_000_000"))
    assert raised.read_text() != text

    _, package = plan(planning(thresholds=load_thresholds(raised)))

    review = next(field for field in package["fields"] if field["key"] == "review_type")
    assert (review["value"], review["provenance"]) == ("Post", "computed")
    assert package["rules"]["review"]["threshold_usd"] == 20_000_000


def test_a_field_added_to_the_schema_is_a_chip_in_its_group_and_removing_it_removes_the_chip(planning, tmp_path):
    schema = (ROOT / "config" / "package_form.toml").read_text()
    added = tmp_path / "with_a_field.toml"
    added.write_text(schema + '\n[[fields]]\nkey = "high_sea_sh_risk"\ngroup = "how"\nkind = "choice"\nsource = "typed"\n'
                     'label = "SEA/SH risk"\nadd_label = "Add the SEA/SH risk"\nstep_field = "High SEA/SH Risk"\n'
                     'options = [{ value = "Yes", label = "High SEA/SH risk" }, { value = "No", label = "Not high" }]\n')
    without = tmp_path / "without_lots.toml"
    lots = schema[schema.index('[[fields]]\nkey = "lots"'):schema.index('[[fields]]\nkey = "country"')]
    without.write_text(schema.replace(lots, ""))

    app = planning(form=load_package_form(added))
    _, with_field = plan(app)
    _, without_lots = plan(planning(form=load_package_form(without)))

    assert [field["key"] for field in with_field["fields"] if field["group"] == "how"][-1] == "high_sea_sh_risk"
    page = call(app, "GET", f"/api/planned-packages/{with_field['package_id']}", ANA).json()
    assert page["form"]["fields"][-1]["label"] == "SEA/SH risk"
    assert "lots" not in [field["key"] for field in without_lots["fields"]]


def test_typing_icb_into_the_method_chip_stores_request_for_bids_with_an_open_international_market_approach(planning):
    app = planning()
    _, package = plan(app)

    changed = call(app, "POST", f"/api/planned-packages/{package['package_id']}", ANA,
                   json={"field": "method", "action": "set", "value": "ICB"}).json()["package"]

    values = {field["key"]: (field["value"], field["provenance"]) for field in changed["fields"]}
    assert values["method"] == ("Request for Bids", "you")
    assert values["market_approach"] == ("Open - International", "you")
    # The market approach says which old method name set it, so the note can say "You chose ICB, so market approach
    # is ..." rather than that you set the market approach (ticket 58; the 15 critique, round 3, follow-up 6).
    [market] = [field for field in changed["fields"] if field["key"] == "market_approach"]
    assert market["via"] == "ICB"
    reopened = call(app, "GET", f"/api/planned-packages/{package['package_id']}", ANA).json()["package"]
    assert reopened["fields"] == changed["fields"]
    # Setting the market approach itself leaves no old name behind.
    direct = call(app, "POST", f"/api/planned-packages/{package['package_id']}", ANA,
                  json={"field": "market_approach", "action": "set", "value": "Open - National"}).json()["package"]
    assert "via" not in next(field for field in direct["fields"] if field["key"] == "market_approach")


def test_a_saved_package_reopens_with_the_same_chips_and_only_for_the_person_who_made_it(planning):
    app = planning()
    _, package = plan(app)

    mine = call(app, "GET", f"/api/planned-packages/{package['package_id']}", ANA)
    theirs = call(app, "GET", f"/api/planned-packages/{package['package_id']}", BEN)

    assert mine.status_code == 200
    assert mine.json()["package"]["fields"] == package["fields"]
    assert mine.json()["package"]["sentence"] == SENTENCE
    assert (theirs.status_code, theirs.json()["code"]) == (404, "unknown_package")


def test_a_change_to_someone_else_s_package_or_one_that_does_not_exist_is_not_found(planning):
    """Ticket 15's review round 3, R5: the server checks the package is the viewer's before it makes a change."""
    app = planning()
    _, package = plan(app)
    change = {"field": "method", "action": "set", "value": "ICB"}

    theirs = call(app, "POST", f"/api/planned-packages/{package['package_id']}", BEN, json=change)
    nobody = call(app, "POST", "/api/planned-packages/pkg-no-such-package", ANA, json=change)

    assert [(answer.status_code, answer.json()["code"]) for answer in (theirs, nobody)] == [(404, "unknown_package")] * 2


@pytest.mark.parametrize("sentence", ["   ", "\t\n"])
def test_a_sentence_of_only_spaces_is_refused_and_nothing_is_planned(planning, sentence):
    """Ticket 15's review round 3, R11: the length is counted after the spaces at each end are removed."""
    app = planning()

    response = call(app, "POST", "/api/planned-packages", ANA, json={"sentence": sentence})

    assert response.status_code == 422
    assert call(app, "GET", "/api/planned-packages", ANA).json()["rows"] == []


def test_a_sentence_with_no_package_in_it_saves_nothing(planning):
    app = planning(case="package-no-package")

    sent, package = plan(app, sentence="what is the weather like in Nairobi")

    assert package is None
    assert ("error", {"code": "no_package"}) in sent
    assert call(app, "GET", "/api/planned-packages", ANA).json()["rows"] == []


def test_a_reader_that_does_not_answer_saves_nothing_and_says_so(planning):
    class Unavailable:
        name, version = "strata-package-reader", None

        def respond(self, items, previous_response_id):
            raise AgentError("agent_unavailable", "The model did not answer.")

    no_reader, unavailable = planning(reader=lambda: None), planning(reader=Unavailable)

    assert ("error", {"code": "no_reader"}) in plan(no_reader)[0]
    assert ("error", {"code": "agent_unavailable"}) in plan(unavailable)[0]
    assert call(unavailable, "GET", "/api/planned-packages", ANA).json()["rows"] == []


def test_a_method_the_form_does_not_list_takes_the_default_and_says_the_sentence_named_another(planning):
    """Ticket 15's verification round 3, V4: a sentence that names "Reverse auction", which the form's Method does
    not list, gets the default, Request for Bids, and the chip says the sentence named a method I don't list, with
    its words, never that the sentence did not say."""
    class NamesAReverseAuction:
        name, version = "strata-package-reader", None

        def respond(self, items, previous_response_id):
            fields = {"category": {"value": "Works", "stated": True}, "country": {"value": "KE", "stated": True},
                      "method": {"value": "Reverse auction", "stated": True}}
            text = json.dumps({"package": True, "dividing": False, "fields": fields})
            return {"id": "resp-reverse-auction",
                    "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}

    _, package = plan(planning(reader=NamesAReverseAuction), sentence="works in Kenya by reverse auction")

    [method] = [field for field in package["fields"] if field["key"] == "method"]
    assert (method["value"], method["provenance"], method["read_as"]) == ("Request for Bids", "unlisted", "Reverse auction")


def test_a_sentence_that_asks_for_lots_to_stay_under_review_gets_the_refusal_and_review_from_the_whole_package(planning):
    _, package = plan(planning(case="package-dividing"),
                      sentence="rural roads, Kenya, about US$15 million, in lots small enough to stay under prior review")

    values = {field["key"]: field["value"] for field in package["fields"]}
    assert package["refusal"] == "dividing"
    assert (values["lots"], values["review_type"]) == (None, "Prior")


def test_setting_the_criteria_yourself_saves_your_sentence_and_no_criteria(planning):
    sent, package = plan(planning(reader=lambda: None), read=False)

    assert [data["id"] for kind, data in sent if kind == "step" and data["status"] == "done"] == ["save"]
    assert [field["value"] for field in package["fields"]] == [None] * len(package["fields"])
    assert package["comparables_query"] is None
    assert package["missing"] == ["category", "country", "method"]


# ── Changing a chip ─────────────────────────────────────────────────────

def change(app, package_id, field, action, value=None, **extra):
    return call(app, "POST", f"/api/planned-packages/{package_id}", ANA,
                json={"field": field, "action": action, "value": value, **extra})


def test_a_smaller_amount_recomputes_review_and_market_approach_and_says_what_changed(planning):
    app = planning()
    _, package = plan(app)

    changed = change(app, package["package_id"], "estimated_amount_usd", "set", 5_000_000).json()["package"]

    values = {field["key"]: field["value"] for field in changed["fields"]}
    assert (values["review_type"], values["market_approach"]) == ("Post", "Open - National")
    assert changed["changed"] == [
        {"field": "market_approach", "from": "Open - International", "to": "Open - National", "cause": "estimated_amount_usd"},
        {"field": "review_type", "from": "Prior", "to": "Post", "cause": "estimated_amount_usd"},
    ]
    # The next change that recomputes nothing leaves no such sentence.
    after = change(app, package["package_id"], "lots", "keep").json()["package"]
    assert after["changed"] == []


def test_the_number_of_lots_never_changes_the_review_type(planning):
    app = planning()
    _, package = plan(app)

    many = change(app, package["package_id"], "lots", "set", 9).json()["package"]

    values = {field["key"]: field["value"] for field in many["fields"]}
    assert (values["lots"], values["review_type"]) == (9, "Prior")
    assert many["changed"] == []


def test_a_change_that_leaves_no_threshold_empties_the_computed_field_and_says_so(planning):
    """The thresholds file gives Kenya a market approach threshold for works only, so goods in Kenya get none: the
    chip asks for one, and the note says why it emptied (review round 2, P18)."""
    app = planning()
    _, package = plan(app)

    goods = change(app, package["package_id"], "category", "set", "Goods").json()["package"]

    market = next(field for field in goods["fields"] if field["key"] == "market_approach")
    assert (market["value"], market["provenance"]) == (None, None)
    assert {"field": "market_approach", "from": "Open - International", "to": None, "cause": "category"} in goods["changed"]


def test_two_changes_at_once_both_stay_saved(planning, fixture_db):
    """A second change that arrives while the first one is still being made starts from the first one's save, so
    neither is lost (review round 2, P1). The country's change reads the World Bank's country list as the viewer,
    which takes a while on the App; the description's change needs no read."""
    import threading
    import time

    slow = threading.Event()

    @contextmanager
    def reading(viewer):
        if slow.is_set():
            time.sleep(0.4)
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = planning(engine_for=reading)
    _, package = plan(app)
    slow.set()
    path = f"/api/planned-packages/{package['package_id']}"

    async def both():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            async def second():
                await asyncio.sleep(0.1)
                return await client.post(path, headers=ANA, json={"field": "description", "action": "set", "value": "Feeder roads"})
            return await asyncio.gather(
                client.post(path, headers=ANA, json={"field": "country", "action": "set", "value": "IN"}), second())

    answers = asyncio.run(both())
    slow.clear()

    assert [answer.status_code for answer in answers] == [200, 200]
    now = call(app, "GET", path, ANA).json()["package"]
    values = {field["key"]: field["value"] for field in now["fields"]}
    assert (values["country"], values["description"]) == ("IN", "Feeder roads")


def test_keeping_the_guess_makes_it_yours_and_leaves_no_guess_to_check(planning):
    app = planning()
    _, package = plan(app)

    kept = change(app, package["package_id"], "lots", "keep").json()["package"]

    lots = next(field for field in kept["fields"] if field["key"] == "lots")
    assert (lots["value"], lots["provenance"], kept["guesses"]) == (2, "you", 0)


def test_a_computed_field_you_set_keeps_your_value_until_you_use_the_computed_one(planning):
    app = planning()
    _, package = plan(app)

    yours = change(app, package["package_id"], "review_type", "set", "Post").json()["package"]
    back = change(app, package["package_id"], "review_type", "use_computed").json()["package"]

    review = next(field for field in yours["fields"] if field["key"] == "review_type")
    assert (review["value"], review["provenance"], review["computed"]) == ("Post", "you", "Prior")
    review = next(field for field in back["fields"] if field["key"] == "review_type")
    assert (review["value"], review["provenance"]) == ("Prior", "computed")


def test_a_value_the_schema_does_not_take_changes_nothing(planning):
    app = planning()
    _, package = plan(app)

    for field, action, value in [("country", "set", "Atlantis"), ("method", "set", "Auction"),
                                 ("plan_months", "set", 61), ("category", "remove", None), ("colour", "set", "blue")]:
        response = change(app, package["package_id"], field, action, value)
        assert (response.status_code, response.json()["code"]) == (422, "invalid_value"), field

    reopened = call(app, "GET", f"/api/planned-packages/{package['package_id']}", ANA).json()["package"]
    assert reopened["fields"] == package["fields"]


def test_the_plan_is_saved_with_whether_it_came_before_the_range(planning):
    app = planning()
    _, package = plan(app)

    change(app, package["package_id"], "plan_months", "set", 6, plan_before_range=True)
    later = change(app, package["package_id"], "plan_months", "set", 9, plan_before_range=False).json()["package"]

    plan_months = next(field for field in later["fields"] if field["key"] == "plan_months")
    assert plan_months["value"] == 9
    # The first plan's answer stands: the person entered a plan before they saw the range.
    assert later["plan_before_range"] is True


# ── Comparables ─────────────────────────────────────────────────────────

def test_the_workflow_ends_with_find_comparables_on_the_criteria_that_pick_comparables(planning):
    sent, package = plan(planning())

    assert [data["id"] for kind, data in sent if kind == "step" and data["status"] == "done"] == [
        "read", "compute", "save", "compare"]
    assert package["comparables_query"] == {"category": "Works", "country": "KE", "method": "Request for Bids"}
    result = next(data["result"] for kind, data in sent if kind == "comparables")
    # Ticket 12's comparables for Kenya's works under Request for Bids: 45 signed and 4 still open
    # (tests/ground_truth/values.toml).
    assert (result["counts"]["signed"], result["counts"]["still_open"]) == (45, 4)
    assert result["package"] is None and result["plan"] is None


def test_a_comparable_opens_in_the_evidence_drawer_with_its_notice_and_its_contract_award(planning):
    app = planning()
    comparables = call(app, "GET", "/api/comparables?category=Works&country=KE&method=Request%20for%20Bids"
                                   "&asof=2026-10-22", ANA).json()
    counted = next(row for row in comparables["rows"] if row["step_reference"] == "KE-MOWI-47509-CW-RFB")

    opened = call(app, "GET", "/api/evidence?id=strata.gold.package:KE-MOWI-47509-CW-RFB&asof=2026-10-22", ANA).json()

    row = opened["row"]
    # tests/ground_truth/values.toml: notice OP00078259 of October 1, 2019, contract 1652775 signed March 23, 2021.
    assert (opened["kind"], opened["stratum"]) == ("package", "What")
    assert (row["notice"]["notice_id"], row["notice"]["notice_date"]) == ("OP00078259", "2019-10-01")
    assert (row["contract"]["contract_id"], row["contract"]["contract_signing_date"]) == ("1652775", "2021-03-23")
    assert (row["months"], row["still_open"]) == (counted["months"], False)
    assert row["datasets"]["notices"]["dataset_name"] == "Procurement Notices"


def test_a_comparable_still_open_opens_with_its_notice_and_no_contract(planning):
    opened = call(planning(), "GET", "/api/evidence?id=strata.gold.package:KE-ICTA-571738-CW-RFB&asof=2026-10-22", ANA)

    row = opened.json()["row"]
    assert (row["notice"]["notice_id"], row["still_open"], row["contract"], row["award_notice"]) == (
        "OP00471871", True, None, None)
    assert row["project_id"] == "P170941"
    # The months run to the as-of date, which the drawer names beside the date the records run through, so the
    # sentence can be checked (design review round 2, F2).
    assert (row["counted_to"], row["canceled"]) == ("2026-10-22", False)


def test_a_canceled_package_opened_by_its_link_says_it_was_left_out_as_canceled(planning):
    """find_comparables leaves a canceled package out (config/thresholds.toml's canceled_as_still_open is false), so
    the drawer must not count it as still open. tests/ground_truth/values.toml: KE-KIMAWASCO-149448-CW-RFB is one of
    the three canceled packages."""
    opened = call(planning(), "GET", "/api/evidence?id=strata.gold.package:KE-KIMAWASCO-149448-CW-RFB&asof=2026-10-22", ANA)

    row = opened.json()["row"]
    assert (row["canceled"], row["process_status"]) == (True, "Canceled")


def test_a_package_no_record_holds_by_the_as_of_date_is_not_found(planning):
    early = call(planning(), "GET", "/api/evidence?id=strata.gold.package:KE-ICTA-571738-CW-RFB&asof=2026-01-01", ANA)

    assert (early.status_code, early.json()["code"]) == (404, "unknown_evidence")


# ── The Packages tab ────────────────────────────────────────────────────

def test_the_packages_tab_lists_the_person_s_packages_with_the_plans_they_checked_newest_first(planning, clock):
    app = planning()
    call(app, "GET", "/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09"
                     "?asof=2026-10-23", ANA)
    clock.move(minutes=5)
    _, package = plan(app)
    call(app, "GET", "/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09"
                     "?asof=2026-10-23", BEN)

    mine = call(app, "GET", "/api/planned-packages", ANA).json()

    assert [row["type"] for row in mine["rows"]] == ["package", "plan_check"]
    first, second = mine["rows"]
    assert (first["package_id"], first["description"], first["country_name"], first["guesses"]) == (
        package["package_id"], "Rural roads", "Kenya", 1)
    # check-plan-p156634-nwwda-2026-10-09.json: the October 9, 2026 plan's nine activities, all checked.
    assert (second["implementing_agency"], second["plan_date"], second["activities"], second["latest"]) == (
        "Northern Water Works Development Agency", "2026-10-09", 9, False)
    # P156634 is Kenya's Water and Sanitation Development Project (tests/ground_truth/values.toml).
    assert second["country_name"] == "Kenya"
    assert mine["counts"] == {"packages": 1, "plan_checks": 1, "total": 2}
    assert call(app, "GET", "/api/planned-packages", BEN).json()["counts"] == {"packages": 0, "plan_checks": 1, "total": 1}


def test_a_preview_of_another_view_records_no_plan_check_and_cannot_plan(planning):
    app = planning()
    call(app, "GET", "/api/projects/P156634/procurement/northern-water-works-development-agency?view=piu", ANA)

    refused = call(app, "POST", "/api/planned-packages", ANA, json={"sentence": SENTENCE, "view": "piu"})

    assert call(app, "GET", "/api/planned-packages", ANA).json()["rows"] == []
    assert (refused.status_code, refused.json()["code"]) == (403, "preview")


def test_the_comparables_route_runs_find_comparables_for_criteria_with_no_step_reference(planning):
    body = call(planning(), "GET", "/api/comparables?category=Works&country=KE&method=Request%20for%20Bids"
                                   "&asof=2026-10-22", ANA).json()

    assert (body["tool"], body["as_of"], body["criteria"]["notice_to"]) == ("find_comparables", "2026-10-22", "2026-10-22")
    assert len(body["rows"]) == 49
    assert body["summary"]["evidence_id"].startswith("strata.tools.find_comparables:@2026-10-22?")


def test_a_size_that_is_no_finite_number_is_refused_on_both_comparables_routes(planning):
    """float() reads inf and nan, which no JSON answer can hold (review round 2, P3)."""
    app = planning()
    for path in ("/api/comparables?category=Works&country=KE", "/api/packages/KE-NWWDA-541055-CW-RFB/comparables?asof=2026-10-22"):
        for value in ("1e400", "nan", "inf"):
            refused = call(app, "GET", f"{path}&size_from_usd={value}", ANA)
            assert (refused.status_code, refused.json()["code"]) == (422, "bad_request"), (path, value)
            assert refused.json()["detail"] == "size_from_usd must be a number."


def test_the_packages_tab_lists_your_packages_when_the_warehouse_refuses_you(planning, fixture_db):
    """A person's own packages come from the app state store, so a warehouse that refuses the viewer leaves their
    packages listed, with no country names (review round 2, P9)."""
    from strata.lakehouse.engine import PermissionDenied

    refusing = {"on": False}

    @contextmanager
    def reading(viewer):
        if refusing["on"]:
            raise PermissionDenied("The warehouse refused this viewer.")
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = planning(engine_for=reading)
    _, package = plan(app)
    refusing["on"] = True

    listed = call(app, "GET", "/api/planned-packages", ANA)

    assert listed.status_code == 200
    rows = listed.json()["rows"]
    assert [(row["package_id"], row["country_name"]) for row in rows] == [(package["package_id"], None)]


def test_the_form_tells_the_workspace_its_limits(planning):
    """The longest plan, the most lots and the longest description are each defined once, in the server, and the
    workspace reads them from the form it is handed (review round 2, P14; CLAUDE.md rule 4)."""
    app = planning()
    _, package = plan(app)

    form = call(app, "GET", f"/api/planned-packages/{package['package_id']}", ANA).json()["form"]

    assert (form["max_months"], form["max_count"], form["text_limit"]) == (60.0, 99, 200)


def test_the_most_lots_and_the_longest_description_come_from_the_thresholds_file(planning, tmp_path):
    """Ticket 15's review round 3, R12: [package_form] in config/thresholds.toml holds both limits (CLAUDE.md rule
    9). With at most 3 lots and descriptions of at most 10 characters, the form says so and the server refuses more."""
    text = (ROOT / "config" / "thresholds.toml").read_text()
    narrower = tmp_path / "thresholds.toml"
    narrower.write_text(text.replace("\ntext_limit = 200\n", "\ntext_limit = 10\n").replace("\nmax_count = 99\n",
                                                                                         "\nmax_count = 3\n"))
    app = planning(thresholds=load_thresholds(narrower))
    _, package = plan(app)
    path = f"/api/planned-packages/{package['package_id']}"

    form = call(app, "GET", path, ANA).json()["form"]
    lots = call(app, "POST", path, ANA, json={"field": "lots", "action": "set", "value": 4})
    words = call(app, "POST", path, ANA, json={"field": "description", "action": "set", "value": "Rural roads in Kenya"})

    assert (form["max_count"], form["text_limit"]) == (3, 10)
    assert [(answer.status_code, answer.json()["code"]) for answer in (lots, words)] == [(422, "invalid_value")] * 2
    assert call(app, "POST", path, ANA, json={"field": "lots", "action": "set", "value": 3}).status_code == 200
