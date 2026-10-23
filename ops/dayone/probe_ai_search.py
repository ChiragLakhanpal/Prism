# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0"]
# ///
"""Day-one test 4: an AI Search endpoint and a hybrid index can be created.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_ai_search.py --env-file .env

It makes the endpoint named in AI_SEARCH_ENDPOINT if it is missing, then a small Delta table of
three passages with their own embedding vectors, as Strata's passages will have. It syncs a
Delta Sync index over that table and asks it one hybrid query, with both words and a vector.
The vectors have the embedding size in config/models.toml, so the index has the same shape
as Strata's. It writes test 4 in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

NEEDS = ["DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "AI_SEARCH_ENDPOINT"]
PASSAGES = [
    ("p1", "The contracts were advertised again after all bids were rejected."),
    ("p2", "The land for the works was secured before the contracts were awarded."),
    ("p3", "The implementing agency signed the contract later than the plan said."),
]
QUERY = "advertised again after the bids were rejected"


def vector(position: int, dimensions: int) -> list[float]:
    """A unit vector that points only at passage `position`, so the right answer is known."""
    count = len(range(position, dimensions, len(PASSAGES)))
    return [(1 / count) ** 0.5 if j % len(PASSAGES) == position else 0.0 for j in range(dimensions)]


def check(search, env: dict, config: dict) -> Outcome:
    names, endpoint = config["names"], env["AI_SEARCH_ENDPOINT"]
    dimensions = dayone.models()["embed"].dimensions
    evidence = []
    try:
        state = search.ensure_endpoint(endpoint)
        evidence.append(f"Endpoint {endpoint}: {state}.")
        if state != "ONLINE":
            return Outcome("failed", f"The endpoint {endpoint} did not come online. Its state was {state}.", evidence)
        passages = [(pid, text, vector(i, dimensions)) for i, (pid, text) in enumerate(PASSAGES)]
        index = search.ensure_index(endpoint, names["search_table"], names["search_index"], dimensions, passages)
        readiness = "ready" if index["ready"] else "not ready"
        evidence.append(f"Index {names['search_index']}: {readiness}, {dayone.count_words(index['rows'], 'row')}, "
                        f"over {names['search_table']}. {index.get('message') or ''}".strip())
        if not index["ready"]:
            return Outcome("failed", "The hybrid index did not become ready.", evidence)
        rows = search.hybrid_query(names["search_index"], QUERY, vector(0, dimensions))
    except SetupError as error:
        return dayone.not_run(error, evidence)
    except ProbeError as error:
        evidence.append(str(error))
        return Outcome("failed", "Making the endpoint, the index or the hybrid query failed.", evidence)
    if not rows:
        return Outcome("failed", "The hybrid query returned no passages.", evidence)
    evidence.append(f"Hybrid query \"{QUERY}\" returned {', '.join(str(row[0]) for row in rows)}, best first.")
    return Outcome("passed", f"The endpoint is online, and the hybrid index answered a hybrid query with "
                             f"{dayone.count_words(len(rows), 'passage')}.", evidence)


class CannedSearch:
    """An endpoint and an index that work, for --dry-run."""

    def __init__(self, env: dict, config: dict):
        pass

    def ensure_endpoint(self, name):
        return "ONLINE"

    def ensure_index(self, endpoint, table, index, dimensions, passages):
        return {"ready": True, "rows": len(passages), "message": ""}

    def hybrid_query(self, index, text, vector):
        return [[pid, text, 0.0] for pid, text in PASSAGES]


def live(env: dict, config: dict):
    from live import LiveSearch
    return LiveSearch(env, config)


def main(argv: list[str] | None = None, service=None) -> int:
    return dayone.run_probe(4, argv, __doc__, NEEDS, live, CannedSearch, check, service)


if __name__ == "__main__":
    sys.exit(main())
