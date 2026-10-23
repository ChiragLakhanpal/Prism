"""The SQL lint (gates/sql_lint.py), a gate step: every query names its tables in three parts
(strata.<schema>.<table>) and takes its values as bound parameters, never built into its text.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def lint():
    spec = importlib.util.spec_from_file_location("sql_lint", ROOT / "gates" / "sql_lint.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tree(tmp_path, **files):
    """A repo-shaped folder: each keyword is a path with / written as __, and its text."""
    for name, text in files.items():
        path = tmp_path / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def test_every_query_in_the_repo_passes_the_lint():
    assert lint().problems(ROOT) == []


def test_a_sql_file_that_names_a_table_in_two_parts_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__lakehouse__gold__package.sql": "SELECT * FROM gold.contract\n"})

    assert lint().problems(root) == [
        "src/strata/lakehouse/gold/package.sql: gold.contract is not a three-part name. "
        "Write it as strata.<schema>.<table>."]


def test_a_common_table_expression_and_a_three_part_name_pass(tmp_path):
    root = tree(tmp_path, **{"tests__ground_truth__check.sql":
                             "WITH latest AS (SELECT * FROM strata.gold.contract) SELECT * FROM latest\n"})

    assert lint().problems(root) == []


def test_a_value_built_into_the_text_of_a_query_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py":
                             "def find(engine, reference):\n"
                             "    return engine.run(f\"SELECT * FROM strata.gold.package WHERE step_reference = '{reference}'\")\n"})

    assert lint().problems(root) == [
        "src/strata/tools/find.py:2: this query's text is built in code. Bind each value as a :name parameter; "
        "a query that builds in only table or column names says so with '# sql-lint: names only'."]


def test_a_query_that_builds_in_only_names_says_so(tmp_path):
    root = tree(tmp_path, **{"src__strata__lakehouse__sync.py":
                             "def count(engine, table):\n"
                             "    return engine.run(f\"SELECT count(*) FROM strata.gold.{table}\")  # sql-lint: names only\n"})

    assert lint().problems(root) == []


def test_a_query_in_a_python_constant_is_read_too(tmp_path):
    root = tree(tmp_path, **{"ops__bundle__check.py": 'RUNS = """\nSELECT task_key FROM ops.pipeline_runs\n"""\n'})

    assert lint().problems(root) == [
        "ops/bundle/check.py:1: ops.pipeline_runs is not a three-part name. Write it as strata.<schema>.<table>."]


BUILT = ("this query's text is built in code. Bind each value as a :name parameter; a query that builds in only "
         "table or column names says so with '# sql-lint: names only'.")


def test_a_value_built_into_a_query_held_in_a_variable_first_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py":
                             "def find(engine, reference):\n"
                             "    sql = f\"SELECT * FROM strata.gold.package WHERE step_reference = '{reference}'\"\n"
                             "    return engine.run(sql)\n"})

    assert lint().problems(root) == [f"src/strata/tools/find.py:2: {BUILT}"]


def test_a_query_held_in_a_variable_inside_a_function_is_read_too(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py":
                             "def find(engine):\n"
                             "    query = \"SELECT * FROM gold.package\"\n"
                             "    return engine.run(query)\n"})

    assert lint().problems(root) == [
        "src/strata/tools/find.py:2: gold.package is not a three-part name. Write it as strata.<schema>.<table>."]


def test_a_three_part_name_outside_the_strata_catalog_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py":
                             "def find(engine, reference):\n"
                             "    return engine.run(\"SELECT * FROM main.default.package WHERE step_reference = :reference\",\n"
                             "                      {\"reference\": reference})\n"})

    assert lint().problems(root) == [
        "src/strata/tools/find.py:2: main.default.package is not in the strata catalog. "
        "Write it as strata.<schema>.<table>."]


def test_a_value_added_or_formatted_into_a_query_anywhere_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py":
                             "def find(reference):\n"
                             "    first = \"SELECT * FROM strata.gold.package WHERE step_reference = '\" + reference + \"'\"\n"
                             "    second = \"SELECT * FROM strata.gold.package WHERE step_reference = '%s'\" % reference\n"
                             "    return \"SELECT * FROM strata.gold.package WHERE step_reference = '{}'\".format(reference)\n"})

    assert lint().problems(root) == [f"src/strata/tools/find.py:{line}: {BUILT}" for line in (2, 3, 4)]


def test_a_docstring_that_starts_with_a_query_word_is_not_a_query(tmp_path):
    root = tree(tmp_path, **{"src__strata__lakehouse__build.py":
                             "def build(engine):\n"
                             "    \"\"\"Create the schemas, then every table.\"\"\"\n"
                             "    message = \"Update the bundle, then deploy again.\"\n"
                             "    return message\n"})

    assert lint().problems(root) == []


# This repo writes its queries as named constants (HELD, NEWEST, PENDING), so a value built into a
# query is most likely built onto one of them.
FIND = ("FIND = \"SELECT * FROM strata.gold.package WHERE step_reference = '{}'\"\n"
        "PERCENT = \"SELECT * FROM strata.gold.package WHERE step_reference = '%s'\"\n"
        "BASE: str = \"SELECT * FROM strata.gold.package\"\n\n\n")


def test_a_value_formatted_or_added_into_a_query_held_in_a_named_constant_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py": FIND +
                             "def find(engine, reference):\n"
                             "    engine.run(FIND.format(reference))\n"
                             "    engine.run(PERCENT % reference)\n"
                             "    return engine.run(BASE + \" WHERE step_reference = '\" + reference + \"'\")\n"})

    assert lint().problems(root) == [f"src/strata/tools/find.py:{line}: {BUILT}" for line in (7, 8, 9)]


def test_a_value_added_onto_a_query_held_in_a_variable_is_refused(tmp_path):
    root = tree(tmp_path, **{"src__strata__tools__find.py":
                             "def find(engine, reference):\n"
                             "    sql = \"SELECT * FROM strata.gold.package\"\n"
                             "    sql += f\" WHERE step_reference = '{reference}'\"\n"
                             "    return engine.run(sql)\n"})

    assert lint().problems(root) == [f"src/strata/tools/find.py:3: {BUILT}"]


def test_names_added_onto_a_named_query_constant_pass_when_the_statement_says_so(tmp_path):
    root = tree(tmp_path, **{"src__strata__lakehouse__sync.py": FIND +
                             "def count(engine, column):\n"
                             "    return engine.run(BASE + f\" ORDER BY {column}\")  # sql-lint: names only\n"})

    assert lint().problems(root) == []
