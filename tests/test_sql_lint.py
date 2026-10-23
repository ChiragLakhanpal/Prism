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
