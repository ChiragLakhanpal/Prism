# 09: The tool registry with the as-of contract, and check_plan

**What to build:** The tool registry, the one seam that every tool, page, workflow and the agent go through, with its first tool, check_plan, and the HTTP route the Check a plan page calls. A tool is defined once: name, description, parameters (always including an optional as-of date), adapter and result shape. Called with the viewer's identity and view, it returns rows with evidence ids, public_from dates and source-line fields, plus a coverage line (how many matched, how many were used, and why the rest were not). The agent's tool list is generated from the registry, so adding a tool later is one entry. check_plan takes a project and an implementing agency's plan (the latest by default, or a named version) and runs the fixed checks from the thresholds file: planned completion passed with no signed contract, with the days left before the project closes; signed late against the first published planned date; actual amount far above the estimate; still pending close to the project's closing date; and the data notes. It returns a mark per package (Needs a look, Watch, Data note or none) with its reasons as structured values, which the screen turns into sentences from the copy file. With an as-of date it uses only plan versions, contracts and project dates public on or before that date.

Read first: docs/PLAN.md sections 6 and 10; ADRs 0002 and 0003; the spec's Seams (seam 2) and "The tool registry and the tools"; docs/agents/areas/agent.md.

**Blocked by:** 07 (Kenya's procurement records, bronze to gold); 08 (P156634's Procurement Plans read into STEP rows)

**Status:** done
**Area:** agent
**Phase:** P1
**Design review:** no

- [ ] A test lists the registry and fails if any tool lacks an as-of parameter or a result shape; the generated agent tool list contains exactly the registry's tools.
- [ ] On the fixture, as of October 22, 2026, check_plan on the NWWDA October 9 plan checks 8 activities and returns: KE-NWWDA-541055-CW-RFB as Needs a look (planned completion July 31, 2026 passed with no signed contract; the project closes October 31, 2026); KE-NWWDA-229129-CW-RFB as Watch (signed 186 days late at about 4 times its estimate); KE-NWWDA-541062-CW-RFQ as Watch (still pending 9 days before closing); three data notes; and two packages with no signals.
- [ ] As of July 1, 2026, KE-NWWDA-541055-CW-RFB is not marked as passing its planned completion, and as of October 1, 2026 the October 9 version is not used.
- [ ] Overriding the days-before-closing threshold in the thresholds file changes KE-NWWDA-541062-CW-RFQ's mark, proving the threshold lives in one place.
- [ ] Every returned row carries an evidence id, a public_from date and its source-line fields (Procurement Plan, agency, version date).
- [ ] The plan-check HTTP route returns the tool's result for the viewer, and a viewer whose token cannot read strata gets a permission error and no rows.
- [ ] The ground-truth SQL for these counts runs in the offline gate.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/09-tool-registry-and-check-plan, as soon as ticket 07 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
- October 23, 2026, merger: merged into build/strata as merge commit f9cc969 (parents 772f59a and bb4a0d9, so the branch's history is kept). The history scan found no keys. The gate passed in 30.1 seconds on the merge commit, and in 29.7 seconds when I ran it again by hand on build/strata. The branch was built in the worktree `.claude/worktrees/wf_e79cc448-4ec-12`, which I removed after the merge. The branch stays.
  - **Evidence.** Review round 2 (`.notes/09-review-r2.md`) approved, with no blocking findings. Verify round 2 (`.notes/09-verify-r2.md`) passed. Criteria 1, 3, 4, 5 and 7 passed offline. Criterion 2 passed on every mark it names: as of October 22, 2026, the tool checked 9 activities and returned 1 Needs a look (KE-NWWDA-541055-CW-RFB), 2 Watch (KE-NWWDA-229129-CW-RFB, 186 days late at 4.15 times its estimate, and KE-NWWDA-541062-CW-RFQ, 9 days before closing), 3 data notes and 3 with no mark. The source plan lists 9 activities on PDF page 3, so this criterion's "8 activities" and "two packages with no signals" are wrong and need the PM to change them to 9 and 3 (decision 1 below). Criterion 6 passed offline: 200 for a viewer with grants, 403 `{"code": "permission"}` with no rows for a token that cannot read strata. Its live half is parked. The ticket's own 47 tests ran in 0.98 seconds. A sweep of 15,846 calls, one for each day from August 1, 2019 to October 23, 2026, found no answer that cites a document that was not yet public.
  - **Workspace results.** None ran, because all 10 keys are missing. I parked three steps in `docs/workspace-catchup.md` as "Ticket 09, step 1 of 3" to "step 3 of 3": turn on user authorization with the `sql` scope, a 403 for a user with no USE CATALOG (and the check for a user with no SELECT), and a 200 equal to `tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09.json`, which also proves the four check_plan SQL files on the warehouse. They run after ticket 06 deploys the App and after ticket 08's live plan run.
  - **Open polish, not blocking.** Review findings R2-P1 to R2-P6 and verify findings V1 to V3 are still open at bb4a0d9. None changes a mark on the NWWDA plan. R2-P2 (a new data note missing from `reasons` in `config/tools.toml` gives HTTP 500 at run time, not a gate failure) matters most for the live change drill. V2 (a delay reason cites only the checked row, not the plan that first gave the planned date) will matter once a plan update moves a step's date.
  - **Decisions parked for the user.**
    1. The October 9 plan lists 9 activities, not 8. The tool checks all 9, leaving 3 with no signals. Pick: change this ticket's criterion 2 and ticket 10's "eight activities" and "two packages folded" to 9 and 3.
    2. A new threshold, `completion_passed_min_estimated_usd = 1_000_000`, keeps KE-NWWDA-541062-CW-RFQ at Watch as the wireframe shows. Any value above US$295,000.00 and up to US$1,230,000.00 gives the same marks. Pick: keep US$1,000,000.
    3. A late signing alone is not marked (NWWDA-WSDP-03-2019-2020 was signed 496 days late and shows no signals, as in the wireframe). Pick: keep it.
    4. Award records are not read, so the check uses only the plan. Pick: keep this until tickets 20 and 23 show "Sources differ".
    5. The `version_not_public` abstention names the later disclosure date, a date after the as-of date. Pick: keep it for page routes, and strip it from agent calls when ticket 13 wires the agent.
    6. "Planned completion passed" uses the first published planned date, not the checked version's own date. Pick: keep it.
    7. Split words in descriptions ("Explor atory Boreholes") show as the PDF gives them. Already parked in docs/STATUS.md item 8.
    8. While an older first listing is not yet public, the signing delay is left out, but the planned completion falls back to the plan's own date. Pick: keep it, since the delay appears once the older plan is disclosed.
    9. An as-of date after today is accepted, and the tool then states events that have not happened (V1). Pick: answer as of today, with `min` against `today()` in `registry.call`. Refusing with HTTP 422 is the other option.
