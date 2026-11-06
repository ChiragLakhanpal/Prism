"""Prism's AI/BI dashboard, "Prism operations", defined in code (the spec's tenth single place; docs/PLAN.md
section 9; tickets 16 and 45).

strata.dashboard.definition holds the dashboard's three pages and their tiles: Data readiness (ticket 16),
Governance and AI quality and adoption (ticket 45). strata.dashboard.render writes them as AI/BI dashboard files:
bundle/dashboards/strata.lvdash.json, "Prism operations", and bundle/dashboards/strata_test.lvdash.json, the test
copy "Prism operations (test)", which bundle/dashboard.yml declares, so the bundle's one deploy command
(ops/bundle/deploy.py) deploys both. The gate checks that each file says what the definition says, and runs every
dataset's query on DuckDB.

Every KPI is defined once, by its query, in the KPI registry (config/kpis.toml). Every word is from the copy file:
copy.dash and copy.kpi (src/strata/dashboard/copy.json), and the Data readiness page's
copy.dataReadiness.server.dashboard. The nightly job writes "What the measures say" and each loop's indicators
(strata.dashboard.findings), and the measure run writes the Data readiness page's snapshot (strata.dashboard.snapshot).

Write the files again after changing the definition, the registry or the words:

    uv run --frozen python -m strata.dashboard --write
"""

from __future__ import annotations

import json
from pathlib import Path

from strata.dashboard import render
from strata.dashboard.definition import DATA_READINESS, PAGES
from strata.dashboard.snapshot import AWARD_ROWS
from strata.dashboard.tiles import COLORS, FIRST
from strata.tools.data_readiness_for import words

FOLDER = Path(__file__).resolve().parents[3] / "bundle" / "dashboards"
FILE = FOLDER / "strata.lvdash.json"
TEST_FILE = FOLDER / "strata_test.lvdash.json"
PARAMETER = "measure_date"
SINGLE = FIRST  # a single-series chart separates nothing by color
# The Data readiness page's datasets, by name (ticket 16).
DATASETS = tuple(render.page_datasets(DATA_READINESS))

__all__ = ["COLORS", "DATASETS", "FILE", "PARAMETER", "SINGLE", "TEST_FILE", "award_datasets", "dashboard", "query",
           "written", "year_labels"]


def query(name: str) -> str:
    """A dataset's query as the gate runs it, without its comment lines and with its placeholders filled."""
    return render.query(name)


def year_labels() -> dict[str, str]:
    """The rows of tiles 4 and 5, by source key or known gap id, in order, from the copy file."""
    return dict(words()["dashboard"]["years"])


def award_datasets() -> tuple[str, ...]:
    """Tile 4's datasets by name, in the order their colors are given."""
    return tuple(year_labels()[key] for key in AWARD_ROWS)


def dashboard(test: bool = False, query_history: bool = True, pages=PAGES) -> dict:
    """The whole dashboard, as an AI/BI dashboard file holds it."""
    return render.render(pages, test=test, query_history=query_history)


def written(test: bool = False, query_history: bool = True) -> str:
    return json.dumps(dashboard(test, query_history), indent=2, ensure_ascii=False) + "\n"
