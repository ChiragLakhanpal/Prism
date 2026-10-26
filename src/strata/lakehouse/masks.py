"""Column masks: the columns of strata.ops that say who did something, which a reader never reads (ticket 64).

The bundle lets the readers group, everyone who can sign in, read every table in strata.ops (bundle/catalog.yml),
so the app can run each query as the viewer (ADR 0003). Two of those tables also say who: who sent each passage
report (strata.ops.candidate_labels) and who asked each question (strata.ops.answer_citations). A review page names a
sender only by role, and a SQL editor must not do better (CLAUDE.md rule 8). MASKED lists those columns, once.

On the warehouse each listed column carries the column mask MASK. It gives the value only to the app's own service
principal, which writes the rows and decides from them whether a report is the viewer's own, and to the user who
deploys, who owns the catalog and whose identity runs the weekly retrieval job that counts reports by person.
Everyone else reads NULL, in what a query selects and in what it filters on alike. ops/app/deploy_app.py makes the
mask and puts it on each column, because only it knows the app's principal. The app reads these two tables as itself
(strata.knowledge.retrieval.reports), and the review pages still name each sender by role.

The fixture has no users, so the gate's stand-in for a reader (tests/retrieval_scenario.py) runs each statement a
viewer runs through as_a_reader(), which reads each masked table through a subquery that gives NULL in its masked
columns, as the mask does.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

TABLES = Path(__file__).resolve().parent / "tables"
MASK = "strata.ops.mask_viewer"  # the mask function, one for every masked column
MASKED: dict[str, tuple[str, ...]] = {
    "strata.ops.candidate_labels": ("viewer_id", "viewer_email"),  # who sent a passage report
    "strata.ops.answer_citations": ("viewer_id",),  # who asked the question an answer answered
    # Ticket 38: an implementing agency's upload is Official Use Only, seen only by its team through the app, so a SQL
    # editor reads none of the officer's words: the file's name, how it was read, and each activity's reference,
    # Description and values. The drafts a team makes, an agency's planned dates and PPSD rows among them, keep their
    # words in the same way: each draft's content, each export's snapshot and each exported file. The app reads all
    # of them as itself (src/strata/uploads/store.py, src/strata/drafts/store.py). A draft's lesson choices keep the
    # author's reason and the rewritten row, which are the draft's words too (ticket 39).
    "strata.ops.uploads": ("uploader_name", "file_name", "reading"),
    "strata.ops.upload_rows": ("activity_reference_no", "description", "content"),
    "strata.ops.drafts": ("content",),
    "strata.ops.draft_exports": ("snapshot",),
    "strata.ops.draft_files": ("content",),
    "strata.ops.draft_lesson_choices": ("reason", "rewrite"),
}


@cache
def columns(table: str) -> tuple[tuple[str, str], ...]:
    """Each column of a table, with its type, in order, from its definition (tables/<schema>/<table>.sql)."""
    import sqlglot
    from sqlglot import exp

    _, schema, name = table.split(".")
    statement = sqlglot.parse_one((TABLES / schema / f"{name}.sql").read_text(), read="databricks")
    return tuple((column.name, column.args["kind"].sql(dialect="databricks"))
                 for column in statement.find_all(exp.ColumnDef))


@cache
def as_a_reader(sql: str) -> str:
    """The statement as a reader runs it with the masks on: each masked table it reads is read through a subquery that
    gives NULL in each masked column. A statement that names no masked table comes back as it was."""
    if not any(table in sql for table in MASKED):
        return sql
    import sqlglot
    from sqlglot import exp

    tree = sqlglot.parse_one(sql, read="databricks")
    for table in list(tree.find_all(exp.Table)):
        name = ".".join(part for part in (table.catalog, table.db, table.name) if part)
        if name not in MASKED:
            continue
        shown = ", ".join(f"CAST(NULL AS {kind}) AS {column}" if column in MASKED[name] else column
                          for column, kind in columns(name))
        masked = sqlglot.parse_one(f"SELECT {shown} FROM {name}", read="databricks")  # sql-lint: names only
        table.replace(masked.subquery(table.alias_or_name))
    return tree.sql(dialect="databricks")
