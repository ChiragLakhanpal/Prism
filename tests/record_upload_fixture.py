"""Writes the upload fixture, tests/fixtures/uploads/nwwda-plan-2026-10-09.csv (ticket 38).

No upload is recorded anywhere, and the Procurement Plan template's tables are not published, so the fixture is the
Northern Water Works Development Agency's plan of October 9, 2026 for P156634, laid out as STEP prints it in a
published plan: a section title (WORKS, GOODS, CONSULTING FIRMS, INDIVIDUAL CONSULTANTS), a header row of STEP's
column and step names, a row of Planned and Actual under each step, then one row per activity.

- The activities and their STEP values are tests/ground_truth/values.toml's [[plan_row]] entries, in the plan's
  order, and the ninth activity [plan] also_lists, KE-NWWDA-207796-CS-INDV, whose values that file's comment gives
  (Post, Individual Consultant Selection, Open, 60,000.00, Completed). Descriptions are written as the plan writes
  them, without the line-wrap spaces its PDF text adds (.notes/08-verify-r2.md F1).
- Each step's Planned and Actual dates, the Loan / Credit No., the Procurement Process and the Prequalification (Y/N)
  are the plan reader's reading of the same plan (strata.silver.plan_steps and plan_rows in the fixture database),
  so the file holds the dates the published plan prints.

Build the fixture database first, then run:

    uv run --frozen python tests/record_upload_fixture.py
"""

import csv
import io
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.reader.step import COLUMNS  # noqa: E402

OUT = ROOT / "tests" / "fixtures" / "uploads" / "nwwda-plan-2026-10-09.csv"
DOCUMENT = "40132287"  # the plan of October 9, 2026 in the fixture database
SECTIONS = ("WORKS", "GOODS", "NON CONSULTING SERVICES", "CONSULTING FIRMS", "INDIVIDUAL CONSULTANTS")
INDIVIDUAL = {"reference": "KE-NWWDA-207796-CS-INDV",
              "description": "consultancy services for environmental safeguards expert", "review_type": "Post",
              "method": "Individual Consultant Selection", "market_approach": "Open",
              "estimated_amount_usd": "60,000.00", "actual_amount_usd": "", "process_status": "Completed"}


def main() -> None:
    truth = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
    written = {row["reference"]: row for row in truth["plan_row"]} | {INDIVIDUAL["reference"]: INDIVIDUAL}
    with DuckDBEngine.open(ROOT / "data" / "out" / "fixture.duckdb", read_only=True) as engine:
        result = engine.run("SELECT section, activity_reference_no, loan_credit_no, procurement_process, prequalification "
                            "FROM strata.silver.plan_rows WHERE document_id = :document_id ORDER BY pdf_page",
                            {"document_id": DOCUMENT})
        rows = [dict(zip(result.columns, row)) for row in result.rows]
        result = engine.run("SELECT activity_reference_no, step, step_order, planned_on, actual_on "
                            "FROM strata.silver.plan_steps WHERE document_id = :document_id "
                            "ORDER BY activity_reference_no, step_order", {"document_id": DOCUMENT})
        steps: dict[str, list[dict]] = {}
        for row in result.rows:
            steps.setdefault(row[0], []).append(dict(zip(result.columns, row)))
    out = io.StringIO()
    sheet = csv.writer(out, lineterminator="\r\n")
    names = list(COLUMNS)
    for section in SECTIONS:
        listed = [row for row in rows if row["section"] == section and row["activity_reference_no"] in written]
        if not listed:
            continue
        order = [step["step"] for step in steps[listed[0]["activity_reference_no"]]]
        sheet.writerow([section])
        sheet.writerow(names + [name for step in order for name in (step, "")])
        sheet.writerow([""] * len(names) + ["Planned", "Actual"] * len(order))
        for row in listed:
            values = written[row["activity_reference_no"]]
            cells = {"Activity Reference No. / Description": f"{values['reference']} / {values['description']}",
                     "Loan / Credit No.": row["loan_credit_no"] or "", "Review Type": values["review_type"],
                     "Method": values["method"], "Market Approach": values["market_approach"],
                     "Procurement Process": row["procurement_process"] or "",
                     "Prequalification (Y/N)": row["prequalification"] or "",
                     "Estimated Amount (US$)": values["estimated_amount_usd"],
                     "Actual Amount (US$)": values["actual_amount_usd"], "Process Status": values["process_status"]}
            dated = {step["step"]: step for step in steps[row["activity_reference_no"]]}
            sheet.writerow([cells.get(name, "") for name in names]
                           + [str(day) if (day := dated[step][head]) else "" for step in order
                              for head in ("planned_on", "actual_on")])
        sheet.writerow([])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out.getvalue(), encoding="utf-8")
    print(f"I wrote {OUT.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
