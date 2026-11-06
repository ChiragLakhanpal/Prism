"""Column masks and row filters: what a reader of strata.ops never reads (tickets 64 and 63).

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

Those two tables also keep what people wrote: each report's question and reason, and each question an answer
answered. FILTERED lists them, each with the reviewer group (a key of config/roles.toml's [groups]) whose workspace
group may read their rows. On the warehouse each carries that group's row filter, row_filter(key), which shows a row
only to the app's principal, the owner and the group's members; everyone else reads no row at all (ticket 63).
ops/app/deploy_app.py makes the filter and puts it on beside the masks, for the same reason.

The fixture has no users, so the gate's stand-in for a reader (tests/retrieval_scenario.py) runs each statement a
viewer runs through as_a_reader(), which reads each masked table through a subquery that gives NULL in its masked
columns, as the mask does, and keeps no row of a filtered table unless the viewer is in its reviewer group.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

TABLES = Path(__file__).resolve().parent / "tables"
MASK = "strata.ops.mask_viewer"  # the mask function, one for every masked column
# The tables whose rows only the app, the owner and one reviewer group read, each with that group's key in the roles file.
FILTERED: dict[str, str] = {
    "strata.ops.candidate_labels": "passage_reviewer",  # each report's question and reason (ticket 32)
    "strata.ops.answer_citations": "passage_reviewer",  # each question an answer answered (ticket 32)
}


def row_filter(group: str) -> str:
    """The row filter function for the tables one reviewer group reads, by the group's key in the roles file."""
    return f"strata.ops.only_{group}"
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
    # Ticket 150: a field photo is Official Use Only, seen only by its uploader's team through the app, so a SQL editor
    # reads none of the staff member's words: the caption, the file's name, their name and the place. The app reads
    # them as itself (src/strata/research/photos.py), and the files sit in a volume the readers group cannot read.
    "strata.ops.field_photos": ("uploader_name", "file_name", "caption", "place"),
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
def as_a_reader(sql: str, groups: frozenset[str] = frozenset()) -> str:
    """The statement as a reader in these reviewer groups (the roles file's keys) runs it with the masks and the row
    filters on: each masked or filtered table it reads is read through a subquery that gives NULL in each masked
    column and, when the reader is not in the table's reviewer group, no row. A statement that names neither comes
    back as it was."""
    if not any(table in sql for table in (*MASKED, *FILTERED)):
        return sql
    import sqlglot
    from sqlglot import exp

    tree = sqlglot.parse_one(sql, read="databricks")
    for table in list(tree.find_all(exp.Table)):
        name = ".".join(part for part in (table.catalog, table.db, table.name) if part)
        if name not in MASKED and name not in FILTERED:
            continue
        hidden = MASKED.get(name, ())
        shown = ", ".join(f"CAST(NULL AS {kind}) AS {column}" if column in hidden else column
                          for column, kind in columns(name))
        kept = " WHERE FALSE" if name in FILTERED and FILTERED[name] not in groups else ""
        masked = sqlglot.parse_one(f"SELECT {shown} FROM {name}{kept}", read="databricks")  # sql-lint: names only
        table.replace(masked.subquery(table.alias_or_name))
    return tree.sql(dialect="databricks")
