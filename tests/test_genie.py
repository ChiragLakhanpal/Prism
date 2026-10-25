"""Genie (ticket 33): the conversation client, the ask_genie tool, the space from code and the metric views.

The live Genie conversation API is a workspace step (docs/workspace-catchup.md). Here a fake workspace plays
its REST answers, with a clock that only moves when the client waits, so a cold warehouse, Genie's own waits,
its rate limit and a result in several chunks all take no real time. The waits the client allows come from
config/thresholds.toml's [genie], which ticket 48 reads too.
"""

import datetime as dt
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from strata.config import load_thresholds
from strata.genie import client as genie_client
from strata.genie import space as genie_space
from strata.lakehouse import catalog
from strata.lakehouse.catalog import CatalogError
from strata.lakehouse.engine import EngineError, PermissionDenied

ROOT = Path(__file__).resolve().parents[1]
METRIC_VIEWS = ROOT / "src" / "strata" / "lakehouse" / "metric_views"
THRESHOLDS = load_thresholds()
SPACE, WAREHOUSE = "01f0aaaabbbbccccddddeeeeffff0000", "wh-strata"
SQL = "SELECT fiscal_year, MEASURE(contracts) AS contracts FROM strata.gold.contract_metrics GROUP BY fiscal_year"
COLUMNS = [{"name": "fiscal_year", "type_name": "INT", "position": 0},
           {"name": "contracts", "type_name": "LONG", "position": 1},
           {"name": "amount_usd", "type_name": "DECIMAL", "position": 2},
           {"name": "share", "type_name": "DOUBLE", "position": 3},
           {"name": "first_signed", "type_name": "DATE", "position": 4},
           {"name": "joint_venture", "type_name": "BOOLEAN", "position": 5},
           {"name": "country", "type_name": "STRING", "position": 6}]
ROWS = [["2021", "69", "86750238.17", "1.2345678E7", "2020-07-03", "true", "KE"],
        ["2022", "41", "71439799.22", "0.25", "2021-07-01", "false", None],
        ["2023", "13", "4766281.32", "3", None, None, "KE"]]


class Clock:
    """Time that moves only when the client sleeps."""

    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeWorkspace:
    """The REST answers of a workspace's SQL warehouse and Genie space, as the docs give their shapes."""

    def __init__(self, clock: Clock, starts_in: float | None = 0, answers_in: float = 12, rate_limited: int = 0,
                 chunk_rows: int = 2, attachments=None, start_allowed: bool = True, status: str = "COMPLETED"):
        self.clock, self.starts_in, self.answers_in = clock, starts_in, answers_in
        self.rate_limited, self.chunk_rows, self.start_allowed, self.status = rate_limited, chunk_rows, start_allowed, status
        self.started_at = None if starts_in else 0.0
        self.asked_at = None
        self.calls: list[tuple[str, str, dict | None]] = []
        self.attachments = attachments if attachments is not None else [
            {"attachment_id": "att-1", "text": {"content": "Here are the contracts by fiscal year."}},
            {"attachment_id": "att-2", "query": {"query": SQL, "statement_id": "stmt-1", "description": "By year"}}]

    def warehouse_state(self) -> str:
        if self.started_at is None:
            return "STOPPED"
        if self.starts_in is None or self.clock() - self.started_at < self.starts_in:
            return "STARTING"
        return "RUNNING"

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict:
        self.calls.append((method, path, body))
        if path == f"/api/2.0/sql/warehouses/{WAREHOUSE}":
            return {"id": WAREHOUSE, "state": self.warehouse_state()}
        if path == f"/api/2.0/sql/warehouses/{WAREHOUSE}/start":
            if not self.start_allowed:
                raise PermissionDenied("The workspace answered 403 to POST start: you lack CAN_MANAGE.")
            self.started_at = self.clock() if self.started_at is None else self.started_at
            return {}
        if path == "/api/2.0/sql/statements/":  # the warm-up a viewer who may not start the warehouse runs
            self.started_at = self.clock() if self.started_at is None else self.started_at
            state = "SUCCEEDED" if self.warehouse_state() == "RUNNING" else "PENDING"
            return {"statement_id": "warm-1", "status": {"state": state}}
        if path == "/api/2.0/sql/statements/warm-1":
            return {"statement_id": "warm-1",
                    "status": {"state": "SUCCEEDED" if self.warehouse_state() == "RUNNING" else "PENDING"}}
        if path.endswith("/start-conversation"):
            if self.rate_limited:
                self.rate_limited -= 1
                raise EngineError(f"The workspace answered 429 to POST {path}: RESOURCE_EXHAUSTED")
            self.asked_at = self.clock()
            return {"conversation_id": "conv-1", "message_id": "msg-1",
                    "message": {"id": "msg-1", "conversation_id": "conv-1", "status": "SUBMITTED"}}
        if path.endswith("/messages/msg-1"):
            waited = self.clock() - self.asked_at
            if self.warehouse_state() != "RUNNING":
                status = "PENDING_WAREHOUSE"
            elif waited < self.answers_in:
                status = "EXECUTING_QUERY"
            else:
                status = self.status
            done = status == "COMPLETED"
            return {"id": "msg-1", "conversation_id": "conv-1", "status": status, "user_id": 1001,
                    "attachments": self.attachments if done else [],
                    "error": {"error": "Genie could not answer."} if status == "FAILED" else None}
        if path.endswith("/attachments/att-2/query-result"):
            return {"statement_response": {
                "statement_id": "stmt-1", "status": {"state": "SUCCEEDED"},
                "manifest": {"schema": {"columns": COLUMNS}, "total_chunk_count": self.chunks()},
                "result": self.chunk(0)}}
        if path.startswith("/api/2.0/sql/statements/stmt-1/result/chunks/"):
            return self.chunk(int(path.rsplit("/", 1)[1]))
        raise AssertionError(f"The fake workspace has no answer for {method} {path}")

    def chunks(self) -> int:
        return -(-len(ROWS) // self.chunk_rows)

    def chunk(self, index: int) -> dict:
        part = {"chunk_index": index, "data_array": ROWS[index * self.chunk_rows:(index + 1) * self.chunk_rows]}
        if index + 1 < self.chunks():
            part["next_chunk_index"] = index + 1
            part["next_chunk_internal_link"] = f"/api/2.0/sql/statements/stmt-1/result/chunks/{index + 1}"
        return part


def ask(workspace: FakeWorkspace, clock: Clock, question: str = "How many contracts were signed each fiscal year?"):
    genie = genie_client.GenieClient(workspace, SPACE, WAREHOUSE, genie_client.Waits.from_thresholds(THRESHOLDS),
                                     sleep=clock.sleep, clock=clock)
    return genie.ask(question)


def test_genie_answers_with_its_sql_and_every_cell_typed_from_the_column_types():
    clock = Clock()
    workspace = FakeWorkspace(clock)

    answer = ask(workspace, clock)

    assert answer.sql == SQL
    assert answer.text == "Here are the contracts by fiscal year."
    assert [name for name, _ in answer.columns] == [column["name"] for column in COLUMNS]
    # Genie returns every cell as text. The verifier matches a sentence's numbers against typed values, so a
    # count is a whole number, an amount keeps its cents, a DOUBLE in Genie's exponent form is read as a number,
    # and a date is a date.
    assert answer.rows == [
        [2021, 69, Decimal("86750238.17"), 12345678.0, dt.date(2020, 7, 3), True, "KE"],
        [2022, 41, Decimal("71439799.22"), 0.25, dt.date(2021, 7, 1), False, None],
        [2023, 13, Decimal("4766281.32"), 3.0, None, None, "KE"]]
    # Three rows came back in two chunks, and the client read both.
    assert [path for _, path, _ in workspace.calls if "/result/chunks/" in path] == [
        "/api/2.0/sql/statements/stmt-1/result/chunks/1"]


def test_a_cold_warehouse_is_started_first_and_the_first_call_answers_within_the_stated_waits():
    clock = Clock()
    workspace = FakeWorkspace(clock, starts_in=8)  # a direct start takes about 8 seconds on Free Edition

    answer = ask(workspace, clock)

    assert answer.rows[0][0] == 2021
    starts = [path for method, path, _ in workspace.calls if method == "POST" and path.endswith("/start")]
    assert starts == [f"/api/2.0/sql/warehouses/{WAREHOUSE}/start"]
    # The question went to Genie only once the warehouse was running, so Genie never waited on it.
    first_question = next(i for i, (_, path, _) in enumerate(workspace.calls) if path.endswith("/start-conversation"))
    assert workspace.calls[first_question - 1][1] == f"/api/2.0/sql/warehouses/{WAREHOUSE}"
    assert workspace.asked_at >= 8
    assert clock() <= (THRESHOLDS.value("genie.warehouse_start_seconds") + THRESHOLDS.value("genie.answer_seconds"))


def test_a_viewer_who_may_not_start_the_warehouse_wakes_it_with_a_query():
    clock = Clock()
    workspace = FakeWorkspace(clock, starts_in=8, start_allowed=False)

    answer = ask(workspace, clock)

    assert answer.rows[1][1] == 41
    assert [path for method, path, _ in workspace.calls if method == "POST" and "statements" in path] == [
        "/api/2.0/sql/statements/"]


def test_a_warehouse_that_never_starts_stops_the_wait_at_the_stated_limit():
    clock = Clock()
    workspace = FakeWorkspace(clock, starts_in=None)

    with pytest.raises(genie_client.GenieError, match="warehouse") as raised:
        ask(workspace, clock)

    assert raised.value.code == "warehouse_cold"
    limit = THRESHOLDS.value("genie.warehouse_start_seconds")
    assert limit <= clock() <= limit + THRESHOLDS.value("genie.poll_seconds")
    assert not any(path.endswith("/start-conversation") for _, path, _ in workspace.calls)


def test_genie_s_rate_limit_is_waited_out_with_a_growing_back_off():
    clock = Clock()
    workspace = FakeWorkspace(clock, rate_limited=2)

    answer = ask(workspace, clock)

    assert answer.rows[2][1] == 13
    first = THRESHOLDS.value("genie.backoff_first_seconds")
    assert workspace.asked_at == first + 2 * first


def test_an_answer_that_takes_too_long_stops_at_the_stated_limit():
    clock = Clock()
    workspace = FakeWorkspace(clock, answers_in=10_000)

    with pytest.raises(genie_client.GenieError) as raised:
        ask(workspace, clock)

    assert raised.value.code == "genie_slow"
    assert clock() <= THRESHOLDS.value("genie.answer_seconds") + THRESHOLDS.value("genie.poll_seconds")


def test_an_answer_with_no_query_is_text_only_and_a_failed_one_says_why():
    clock = Clock()
    text_only = FakeWorkspace(clock, attachments=[{"attachment_id": "att-1",
                                                   "text": {"content": "Which country do you mean?"}}])

    answer = ask(text_only, clock)

    assert (answer.sql, answer.rows, answer.text) == (None, [], "Which country do you mean?")
    clock = Clock()
    with pytest.raises(genie_client.GenieError) as raised:
        ask(FakeWorkspace(clock, status="FAILED"), clock)
    assert raised.value.code == "genie_failed"


# ── The metric views ─────────────────────────────────────────────────────

def test_each_metric_view_is_a_databricks_statement_with_no_semicolon_over_gold_tables():
    views = catalog.metric_view_definitions()

    assert [view.full_name for view in views] == ["strata.gold.contract_metrics", "strata.gold.package_metrics"]
    for view in views:
        assert view.sql.startswith(f"CREATE OR REPLACE VIEW {view.full_name}\nWITH METRICS\nLANGUAGE YAML\nAS $$\n")
        assert view.sql.endswith("\n$$")
        # The SQL task cuts a file at every semicolon outside quotes, so the body holds none.
        assert ";" not in view.sql
        assert "#" not in view.sql.split("$$")[1], "the YAML's comment lines stay in the repo"


@pytest.mark.parametrize("old, new, says", [
    ("expr: COUNT(1)", "expr: COUNT(1);", "semicolon"),
    ("name: country_record\n    source", "name: country_code\n    source", "join named country_code"),
    ("source: strata.gold.contract\n", "source: strata.silver.awards\n", "gold table"),
], ids=["a-semicolon", "a-join-named-like-a-dimension", "a-source-outside-gold"])
def test_a_metric_view_that_breaks_a_rule_is_refused_with_the_fix(tmp_path, old, new, says):
    folder = tmp_path / "metric_views"
    shutil.copytree(METRIC_VIEWS, folder)
    target = folder / "gold" / "contract_metrics.yaml"
    assert old in target.read_text()
    target.write_text(target.read_text().replace(old, new, 1))

    with pytest.raises(CatalogError, match=says):
        catalog.metric_view_definitions(folder)


def test_the_deploy_step_creates_each_metric_view():
    ran = []

    class Recording:
        name = "databricks"

        def run(self, sql, params=None):
            ran.append(sql)

    built = catalog.build_metric_views(Recording())

    assert built == ["strata.gold.contract_metrics", "strata.gold.package_metrics"]
    assert [sql.split("\n")[0] for sql in ran] == [f"CREATE OR REPLACE VIEW {name}" for name in built]


# ── The space from code ──────────────────────────────────────────────────

def genie_questions() -> list[dict]:
    from strata.evals import benchmark

    return [question for question in benchmark.load() if question.get("tool") == "ask_genie"]


def test_the_space_reads_the_metric_views_with_its_trusted_sql_and_the_benchmark_s_genie_questions():
    space = genie_space.load()
    body = genie_space.serialized(space)

    tables = [table["identifier"] for table in body["data_sources"]["tables"]]
    assert tables == sorted(["strata.gold.contract_metrics", "strata.gold.package_metrics",
                             "strata.gold.contract_supplier"])
    # Exactly one text instruction.
    assert len(body["instructions"]["text_instructions"]) == 1
    trusted = body["instructions"]["example_question_sqls"]
    assert len(trusted) == len(space.trusted) >= 5
    for example in trusted:
        sql = "\n".join(example["sql"])
        named = set(re.findall(r"strata\.\w+\.\w+", sql))
        assert named and named <= set(tables), f"{example['question']} reads {named}"
        # MEASURE() stays in the trusted SQL; a question about a plain table needs none.
        assert "MEASURE(" in sql or named <= set(space.tables)
    asked = sorted(question["arguments"]["question"] for question in genie_questions())
    assert len(asked) >= 5
    assert sorted(item["question"][0] for item in body["benchmarks"]["questions"]) == asked
    for item in body["benchmarks"]["questions"]:
        answer = "\n".join(item["answer"][0]["content"])
        # Each answer is its ground-truth SQL with its parameters written in and its comment lines left out.
        assert "MEASURE(" not in answer and "--" not in answer
        assert not re.search(r"(?<![:\w]):[a-z_]+", re.sub(r"'[^']*'", "", answer))


def test_every_id_comes_from_a_stable_key_and_every_list_is_sorted_by_id_or_identifier():
    first, again = genie_space.serialized(genie_space.load()), genie_space.serialized(genie_space.load())

    assert first == again
    lists = [first["config"]["sample_questions"], first["instructions"]["example_question_sqls"],
             first["instructions"]["text_instructions"], first["benchmarks"]["questions"]]
    ids = [item["id"] for items in lists for item in items]
    assert all(re.fullmatch(r"[0-9a-f]{32}", item) for item in ids)
    assert len(ids) == len(set(ids))
    for items in lists:
        assert [item["id"] for item in items] == sorted(item["id"] for item in items)


class FakeSpaces:
    """Genie's space API in memory. Like Genie, it hands the serialized space back with fields of its own added
    and its keys in another order."""

    def __init__(self, spaces: dict | None = None):
        self.spaces = spaces or {}
        self.created, self.updated = [], []

    def list_spaces(self):
        return [{"space_id": key, "title": value["title"]} for key, value in self.spaces.items()]

    def get_space(self, space_id):
        if space_id not in self.spaces:
            raise LookupError(space_id)
        found = dict(self.spaces[space_id])
        if "serialized_space" in found:
            body = json.loads(found["serialized_space"])
            for table in body.get("data_sources", {}).get("tables", []):
                table["column_configs"] = []
            found["serialized_space"] = json.dumps(dict(reversed(list(body.items()))))
        return {"space_id": space_id, **found}

    def create_space(self, body):
        space_id = f"{len(self.spaces) + 1:032x}"
        self.spaces[space_id] = dict(body)
        self.created.append(space_id)
        return {"space_id": space_id, **body}

    def update_space(self, space_id, body):
        self.spaces[space_id] = dict(body)
        self.updated.append(space_id)
        return {"space_id": space_id, **body}


TAXI = "0f0e0d0c0b0a09080706050403020100"


def test_the_space_deploys_from_code_and_a_second_deploy_reports_no_change():
    api, space = FakeSpaces(), genie_space.load()

    first = genie_space.deploy(api, space, WAREHOUSE, None)
    second = genie_space.deploy(api, space, WAREHOUSE, first.space_id)

    assert (first.action, second.action) == ("created", "unchanged")
    assert second.space_id == first.space_id
    assert api.updated == [] and second.changes == []


def test_a_changed_instruction_updates_strata_s_space_and_says_what_changed():
    api, space = FakeSpaces(), genie_space.load()
    first = genie_space.deploy(api, space, WAREHOUSE, None)

    changed = genie_space.deploy(api, genie_space.replace(space, instruction=space.instruction + " Be brief."),
                                 WAREHOUSE, first.space_id)

    assert (changed.action, api.updated, changed.changes) == ("updated", [first.space_id], ["the text instruction"])


def test_a_space_whose_title_is_not_strata_s_is_never_changed_and_strata_gets_its_own():
    taxi = {"title": "Taxi trips", "warehouse_id": WAREHOUSE, "description": "samples.nyctaxi.trips"}
    api = FakeSpaces({TAXI: dict(taxi)})

    deployed = genie_space.deploy(api, genie_space.load(), WAREHOUSE, TAXI)

    assert deployed.action == "created" and deployed.space_id != TAXI
    assert api.spaces[TAXI] == taxi and api.updated == []
    assert deployed.notes == [f"The space {TAXI} is titled Taxi trips, which is not Strata's, so I left it as it was."]
    # The next deploy finds Strata's space by its title, even while the env file still names the taxi space.
    again = genie_space.deploy(api, genie_space.load(), WAREHOUSE, TAXI)
    assert (again.action, again.space_id) == ("unchanged", deployed.space_id)


def test_the_new_space_id_is_appended_to_the_env_file_and_nothing_else_in_it_changes(tmp_path):
    env = tmp_path / "env-file"
    env.write_text(f"DATABRICKS_HOST='https://example.cloud.databricks.com'\nGENIE_SPACE_ID='{TAXI}'")
    before = env.read_text()

    genie_space.append_env(env, "GENIE_SPACE_ID", "00000000000000000000000000000001")

    # The file had no final line break, so the appended line starts on a line of its own. A later line wins
    # when the live commands read the file (ops/dayone/dayone.py, load_env).
    assert env.read_text() == before + "\nGENIE_SPACE_ID='00000000000000000000000000000001'\n"


# ── ask_genie, through the tool registry (seam 2) ────────────────────────

from strata.dbx import Viewer  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.tools import registry  # noqa: E402

ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as opened:
        yield opened


def ask_genie(engine, question, **arguments):
    return registry.call("ask_genie", {"question": question, **arguments}, registry.Context(engine=engine, viewer=ANA))


def test_ask_genie_returns_typed_rows_each_with_a_stable_evidence_id_and_its_source_line(engine):
    [question] = [item for item in genie_questions() if item["id"] == "genie-joint-venture-1624689"]

    first = ask_genie(engine, question["arguments"]["question"], as_of="2026-10-23")
    again = ask_genie(engine, question["arguments"]["question"], as_of="2026-10-23")

    assert first["abstention"] is None
    # The two members of the joint venture, from values.toml's [awkward.joint_venture], each amount a decimal
    # with its cents, as the verifier's first check reads a row's numbers.
    assert [row["values"] for row in first["rows"]] == [
        {"supplier_id": "503708", "supplier_contract_amount_usd": "697972.33"},
        {"supplier_id": "503711", "supplier_contract_amount_usd": "697972.33"}]
    assert [row["evidence_id"] for row in first["rows"]] == [row["evidence_id"] for row in again["rows"]]
    assert all(re.fullmatch(r"strata\.genie:[0-9a-f]{16}/\d+", row["evidence_id"]) for row in first["rows"])
    assert first["rows"][0]["source"] == {"space": genie_space.load().title, "sql": first["sql"]}
    assert "strata.gold.contract_supplier" in first["sql"]
    assert first["columns"] == [{"name": "supplier_id", "type": "STRING"},
                                {"name": "supplier_contract_amount_usd", "type": "DECIMAL"}]
    # Every row is dated by the newest record of the tables Genie reads: on or before the as-of date (ADR 0002).
    assert {row["public_from"] for row in first["rows"]} == {first["records_through"]}
    assert first["records_through"] <= "2026-10-23"


def test_ask_genie_types_whole_numbers_and_dates_so_a_sentence_s_numbers_can_match_them(engine):
    [question] = [item for item in genie_questions() if item["id"] == "genie-contract-ke-nwwda-229129"]

    result = ask_genie(engine, question["arguments"]["question"], as_of="2026-10-23")

    assert [row["values"] for row in result["rows"]] == [
        {"contract_signing_date": "2022-01-03", "contract_amount_usd": "1245092.76"}]
    [counts] = ask_genie(engine, [item for item in genie_questions()
                                  if item["id"] == "genie-kenya-contracts-since-fy2020"][0]["arguments"]["question"],
                         as_of="2026-10-23")["rows"]
    assert counts["values"] == {"contracts": 603, "with_step_reference": 528}


def test_ask_genie_gives_no_rows_for_an_as_of_date_before_the_newest_record_it_reads(engine):
    """Genie cannot be trusted to filter on public_from, so it answers only when nothing it reads is newer."""
    [question] = [item for item in genie_questions() if item["id"] == "genie-kenya-contracts-since-fy2020"]

    result = ask_genie(engine, question["arguments"]["question"], as_of="2024-12-31")

    assert result["rows"] == [] and result["sql"] is None
    assert result["abstention"]["reason"] == "as_of_before_records"
    assert result["abstention"]["records_through"] > "2024-12-31"


def test_a_question_genie_writes_no_query_for_is_not_answered(engine):
    result = ask_genie(engine, "Which supplier is the best?", as_of="2026-10-23")

    assert (result["rows"], result["abstention"]["reason"]) == ([], "not_answered")


class ViewerEngine:
    """The engine the app opens for a viewer on the workspace: the SQL warehouse, with a transport that carries
    that viewer's token and nothing else (src/strata/server/engines.py)."""

    name = "databricks"

    def __init__(self, transport, fixture):
        self.transport, self.warehouse_id, self.fixture = transport, WAREHOUSE, fixture

    def run(self, sql, params=None):
        return self.fixture.run(sql, params)


def test_on_the_workspace_ask_genie_asks_as_the_viewer_through_the_viewer_s_own_transport(engine, monkeypatch):
    clock = Clock()
    workspace = FakeWorkspace(clock, starts_in=8)
    monkeypatch.setenv("GENIE_SPACE_ID", SPACE)
    monkeypatch.setattr(genie_client.time, "sleep", clock.sleep)
    monkeypatch.setattr(genie_client.time, "monotonic", clock)

    result = registry.call("ask_genie", {"question": "How many contracts were signed each fiscal year?"},
                           registry.Context(engine=ViewerEngine(workspace, engine), viewer=ANA,
                                            as_of=dt.date(2026, 10, 23)))

    # Every call went through the viewer's transport: the warehouse started first, then Genie answered.
    assert workspace.calls[0][1] == f"/api/2.0/sql/warehouses/{WAREHOUSE}"
    assert any(path == f"/api/2.0/genie/spaces/{SPACE}/start-conversation" for _, path, _ in workspace.calls)
    assert [row["values"]["contracts"] for row in result["rows"]] == [69, 41, 13]
    assert result["rows"][1]["values"]["country"] is None
    assert clock() <= THRESHOLDS.value("genie.warehouse_start_seconds") + THRESHOLDS.value("genie.answer_seconds")


def test_with_no_genie_space_named_ask_genie_says_genie_is_unavailable(engine, monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_ID", raising=False)

    result = registry.call("ask_genie", {"question": "How many contracts?"},
                           registry.Context(engine=ViewerEngine(FakeWorkspace(Clock()), engine), viewer=ANA,
                                            as_of=dt.date(2026, 10, 23)))

    assert (result["rows"], result["abstention"]["reason"]) == ([], "genie_unavailable")
