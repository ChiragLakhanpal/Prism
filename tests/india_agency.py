"""P130164 with a Procurement Plan, on a copy of the fixture (ticket 133).

The fixture records no Procurement Plan for P130164; the workspace's is the plan of June 20, 2018, which names its
implementing agency "Public Works Department", while the projects API record names "Rajasthan State Public Works
Department" (data/fixture/recorded/api/projects/P130164.json). So a copy of the fixture gives P130164 two plan versions
with the workspace plan's spelling: the Coast Water Services Board's plans of July 31 and August 17, 2026 (documents
40119876 and 40122770, with 7 and 8 activities), moved from P156634 and renamed. tests/test_agency_names.py checks the
routes on it, and tests/record_agency_names_api.py writes the Procurement tab's answers the screen test serves.
"""

import shutil
from contextlib import contextmanager
from pathlib import Path

from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app

INDIA_PLAN = "Public Works Department"  # the plan of June 20, 2018 on the workspace
INDIA_RECORD = "Rajasthan State Public Works Department"  # the projects API record
MOVED = ("40119876", "40122770")
DAY = "asof=2026-10-23"
# The Procurement tab's answers on the copy, by the file tests/record_agency_names_api.py writes each to.
RECORDED = {"project-p130164-one-agency.json": f"/api/projects/P130164?{DAY}",
            "packages-p130164-one-agency.json": f"/api/projects/P130164/packages?{DAY}"}


def give_p130164_a_plan(fixture_db: Path, folder: Path) -> Path:
    """A copy of the fixture database in the folder, with the two plans moved to P130164."""
    database = folder / "fixture.duckdb"
    shutil.copy(fixture_db, database)
    moved = {"one": MOVED[0], "two": MOVED[1]}
    with DuckDBEngine.open(database) as engine:
        engine.run("UPDATE strata.silver.plan_versions SET project_id = :pid, implementing_agency = :agency "
                   "WHERE document_id IN (:one, :two)", {"pid": "P130164", "agency": INDIA_PLAN, **moved})
        for table in ("plan_rows", "plan_steps", "plan_step_delays", "plan_listings", "plan_data_notes"):
            engine.run(f"UPDATE strata.silver.{table} SET project_id = :pid WHERE document_id IN (:one, :two)",  # sql-lint: names only
                       {"pid": "P130164", **moved})
    return database


def app_on(database: Path):
    """The app on a database, read-only, as each viewer."""
    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(database, read_only=True) as engine:
            yield engine
    return create_app(engine_for=engine_for)
