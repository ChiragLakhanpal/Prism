# 68: Dashboard tiles that Lakeview rejects with "Invalid widget definition is imported."

**What to build:** The deployed Strata dashboard (ticket 16's Data readiness page, deployed by the bundle from `bundle/dashboards/strata.lvdash.json`) shows "Invalid widget definition is imported." on some tiles when the user opens it in the workspace on October 25, 2026. `src/strata/dashboard/__init__.py` writes that file from code: two text boxes as `multilineTextboxSpec` with `lines`, three tables as widget version 1, three bar charts as version 3, one pivot as version 3 and one date filter as version 2. Find which of these Lakeview rejects and fix the writer so every tile renders. Do it with evidence, not guesses: ask the second session (which holds the workspace keys) to export a small dashboard made in the workspace UI with one of each widget type, or to fetch the deployed dashboard's JSON, and compare the shapes field by field; the user can name the tiles that show the message. Save the known-good shapes as a fixture and add a test that every widget the writer produces matches them in type, version and required fields. Ticket 45 adds the Governance and AI quality pages through the same writer, so build on its merged code. The live proof is the bundle deploy of the dashboard and a look at every page in the UI, which the second session records in `docs/workspace-catchup.md`. Change no measure and no dataset query.

Read first: `src/strata/dashboard/__init__.py` and `snapshot.py`; `bundle/dashboard.yml`; `bundle/dashboards/strata.lvdash.json`; ticket 16's and 45's done comments and `.notes/16-verify*.md`; the Lakeview dashboard JSON examples in the Databricks documentation the repo's README links, if any.

**Blocked by:** 45 (All three dashboard pages and the KPIs)

**Status:** ready-for-agent
**Area:** data
**Phase:** P2
**Design review:** no

- [ ] A fixture of known-good widget shapes (exported from the workspace, with its source named in the file) and a test that every widget the writer produces matches its shape's type, version and required fields; the test fails on the writer as it is today and passes after the fix.
- [ ] After the bundle deploy, no tile on any of the three pages shows "Invalid widget definition is imported." (recorded by the second session or the user in the catch-up file under this ticket's heading).
- [ ] The dataset queries and the measures are unchanged, and ticket 16's awards-row check still holds.

## Comments

- October 25, 2026, orchestrator: opened at 22:00 PDT when the user saw the message on the deployed dashboard. Waits on ticket 45, which is in verification; dispatched in the next restart of the wave after 45 merges.
