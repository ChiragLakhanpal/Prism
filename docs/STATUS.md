# Strata build status

_Kept current by the `pm` agent. Last updated at 09:25 Pacific time on Friday, October 23, 2026, from commit 4b5e54f on `build/strata`._

## Today

Two more tickets reached `build/strata` in wave 3. Ticket 50, the gate lanes, merged at 1c6aa51 at 06:47, and its verification passed 8 of 8 criteria. Ticket 08, P156634's Procurement Plans as STEP rows, merged at eba87ed at 08:07, and its verification passed 6 of 6 criteria on the fixture with three live checks parked. The other two tickets in the wave went back to the orchestrator. Ticket 07's round 4 verification failed criterion 3, because 49 notices write a credit in an older form, such as `6030-KE`, that gold does not read as its project's credit. Ticket 02's round 7 review found one blocking test helper that does not wait for the font, so a tab test fails about once in 30 gate runs, while its round 7 critique scored nothing below 4. Phase P0 is still open, because 02 has not merged and none of the ten day-one tests has run. The gate passed on `build/strata` in 33.4 seconds when the PM ran it at 09:21. The file `.env` is still missing, and all 10 keys that `.env.example` lists are unset (`python3 .claude/hooks/guard.py --env-keys` at 09:18). Ten workspace steps now wait in `docs/workspace-catchup.md`. The offline build is on track, with 13 build rounds of work left and 14 days to the Round 2 date the PM assumes. The live half is at risk until the user runs the wizard.

## Phase

P0 Foundations is still open, and P1 Walking skeleton runs beside it. Both come from `docs/PLAN.md` section 13. The tickets' Phase lines count 5 tickets in P0, 12 in P1 (ticket 50 among them), 29 in P2, 2 in P3 and 2 in P4, which makes 50.

### P0 Foundations

Exit criterion:

- [ ] Every day-one test has a result and a chosen path. Not met. All ten tests in `docs/day-one-results.md` say "not run", read at 09:18. Ticket 03's second criterion says the user fills it by running the wizard and the probes.

The phase's work, as `docs/PLAN.md` section 13 lists it:

- [x] The repo with its rules, hooks and gate. Ticket 01 merged at 45a8298, and round 3's verification passed 9 of 9 criteria (`.notes/01-verify-r3.md`).
- [ ] The `strata` catalog. Ticket 04 merged its offline half at 01a7286. Its criteria 1, 2, 3, 4 and 7 stay parked until the bundle is deployed (`.notes/04-verify-r3.md`).
- [ ] The day-one tests, the model deployments, the Azure caps and pay-as-you-go before November 10. Ticket 03's wizard and probes landed at 43ed569, and its criteria 2 to 5 are parked (`.notes/03-verify-r5.md`). `docs/day-one-results.md` says "Not done yet" for pay-as-you-go and "not checked" for the caps.
- [ ] The design-system foundation, ticket 02. It is still in progress after seven review rounds. See "In flight".
- [x] The demo and showcase fixtures, ticket 05. It merged at f961131, and round 3's verification passed 7 of 7 criteria (`.notes/05-verify-r3.md`).

The P0 phase gate did not run in this wave, because 02 has not merged. It runs as soon as 02 merges, and it can pass only after the user's wizard and probes.

### P1 Walking skeleton

Exit criteria:

- [ ] The deployed app checks one plan. Not met. Tickets 06, 09 and 10 have not started.
- [ ] The deployed app answers one question with citations. Not met. Tickets 11, 13 and 14 have not started.
- [x] The offline gate runs in under two minutes. It holds today. The PM's run on `build/strata` at 4b5e54f passed in 33.4 seconds at 09:21. The P1 phase gate checks it again when P1's last ticket merges.

Two of P1's 12 tickets are done, 50 and 08. The P1 phase gate runs when every P1 ticket has merged, so it did not run in this wave. The deployed app needs the workspace and Foundry, so offline work alone cannot meet P1's exit.

Ticket 50 is not scope creep. The orchestrator opened it in commit 5bfaaae to keep the gate under two minutes, which the spec allows ("If the screen tests threaten that budget they run in parallel workers").

## Frontier

The frontier is every `ready-for-agent` ticket whose blockers are all `done`, with ticket 03 counted as satisfied. The ticket with the longest chain of tickets waiting on it goes first, and the lowest number breaks ties, as the standing rules in `docs/agents/build.md` say.

No new ticket is on the frontier right now. Every `ready-for-agent` ticket waits on 02 or on 07, so those two come first.

1. Ticket 07, Kenya's procurement records. 41 tickets wait on it. Its chain is the longest, at 13 tickets: 07, 09, 11, 13, 14, 15, 30, 34, 44, 45, 46, 47 and 49. Each extra build round that 07 takes moves the end of the build by one round.
2. Ticket 02, the design-system foundation. 37 tickets wait on it, and its chain is 12 tickets: 02, 06, 10, 12, 15, 30, 34, 44, 45, 46, 47 and 49. It can take one more build round than 07 without moving the end. A second extra round moves the end by one round.

When 07 merges, ticket 09 (38 waiting, chain 12) and ticket 17 (31 waiting, chain 10) join the frontier, in that order. When 02 merges, ticket 06 (36 waiting, chain 11) joins.

What the next builders need:

- Ticket 09 is the first tool that reads `plan_step_delays`. Ticket 08's verification finding F2 says a delay row's `public_from` should be the later of its own plan's date and its first listing's date before any as-of answer reads it. No recorded plan triggers it yet. The finding is in ticket 08's merger comment.
- Ticket 10 shows the plan's descriptions. Ticket 08's finding F1 says wrapped words stay split, as in "Explor atory". Decision 8 covers it.
- Ticket 16 reads the latest-activities measures. Ticket 08's finding F3 says NWWDA-WSDP-03-2019-2020 is in two agencies' latest plans, so the measures count 46 pairs for 45 activities. Review polish S5 asks to rename `latest_activities_with_first_listing_read` before ticket 16 reads it.
- Ticket 06 still owes the check that ticket 01's verification asked for. Inside the deployed app, `GET /api/me` must name the viewer and return `"has_token": true`, never the token.
- `.notes/later-wave-notes.md` holds lines for tickets 12, 15, 23, 26, 27, 38, 41 and 45. The orchestrator copies each into its ticket's notes when that wave starts.

## In flight

| Ticket | Branch and worktree | In progress since | Where it stands |
|---|---|---|---|
| 07, Kenya's procurement records | `strata/07-kenya-procurement-records` in `.claude/worktrees/wf_1a4ee1cf-75b-3`, tip 620efd2 from 08:54 | 06:22 on October 23, commit 63ed9bd, so 2 hours 59 minutes at 09:21 | Needs the orchestrator. Review round 4 approves with no blocking findings and three polish items (`.notes/07-review-r4.md`). Verification round 4 passes seven criteria, parks one for the workspace and fails criterion 3 (`.notes/07-verify-r4.md`). Gold stores credit 6030 as `IDA6030` on 6 notices, gives 33 more P156634 notices and 8 P130164 notices no loan, and stores credit 5268 two ways. The verifier's fix has four steps, in `clean.py`, in `gold/notice.sql`, in `values.toml` with the four-forms test, and in `docs/PLAN.md` section 3. Review polish P1 names seven phone labels the stripper does not know yet. The branch's gate passed in 48.0 seconds. |
| 02, the design-system foundation | `strata/02-design-system-foundation` in `.claude/worktrees/wf_3754dbdb-163-2`, tip 3d61fe0 from 07:08 | 02:55 on October 23, commit e48667e, so 6 hours 26 minutes at 09:21 | Needs the orchestrator. Review round 7 asks for changes, with one blocking finding and three polish items (`.notes/02-review-r7.md`). Finding B1 says `fontsSettled` in `web/tests/gallery-components.spec.ts` does not wait for Open Sans. In 30 gate runs one failed in the Playwright step, and the review gives a four-line fix. Critique round 7's lowest score is 4, so nothing in the design blocks the merge (`.notes/02-critique-r7.md`). No verifier result exists yet. The branch's merge base is 9c42e69, so it must merge `build/strata` again to take in ticket 08. |

Ticket 03 is `ready-for-human`, so no agent works on it. It waits for decision 1.

## Done (P0 and P1)

A ticket counts as done only when its file says `done`, it is merged into `build/strata`, and its verifier result passed.

| Ticket | Phase | Status commit | Merge commit | Verification | Proven on the workspace |
|---|---|---|---|---|---|
| 01, the repo scaffold and offline gate | P0 | e686398 | 45a8298 | Round 3 passed 9 of 9 criteria | It has no workspace step |
| 05, the demo and showcase fixtures | P0 | 78a65bf | f961131 | Round 3 passed 7 of 7 criteria | It has no workspace step |
| 04, the catalog and bundle skeleton | P0 | 5a0fa3a | 01a7286 | Round 3 passed criteria 5 and 6, parked 1, 2, 3, 4 and 7, and failed none | Not yet. Catch-up steps 1 to 4 for ticket 04 must run first |
| 50, gate lanes | P1 | 9c42e69 | 1c6aa51 | Round 3 passed 8 of 8 criteria, with none parked (`.notes/50-verify-r3.md`) | It has no workspace step |
| 08, P156634's plans as STEP rows | P1 | 4b5e54f | eba87ed | Round 2 passed 6 of 6 criteria on the fixture and parked three live checks (`.notes/08-verify-r2.md`) | Not yet. Catch-up steps 1 and 2 for ticket 08 must run first |

Tickets 04 and 08 count as done for the frontier. Their parked criteria and checks stay unproven until the catch-up runs and the verifier re-checks them.

Ticket 03 is not done. Its file says `ready-for-human`, set in commit 79a3ab3, and its criteria 2 to 5 are parked.

From dispatch to merge, the six tickets that landed took 1 hour 46 minutes (01), 3 hours 32 minutes (03), 2 hours 30 minutes (05), 2 hours 23 minutes (04), 1 hour 29 minutes (50) and 1 hour 45 minutes (08). That averages 2 hours 14 minutes a ticket. The dispatch and merge commits are in `git log build/strata`.

The gate on `build/strata` passed in 28.9 seconds after ticket 50's merge at 06:48 and in 40.3 seconds after ticket 08's merge at 08:08, both in the merger comments. The PM's run at 09:21 passed in 33.4 seconds. The Python tests under `tests/` and `ops/bundle/tests/` took 31.2 seconds of that and set the total.

Parked live checks, from `docs/workspace-catchup.md`:

- Ticket 03, steps 1 to 4: the unit of a Global Batch capacity, bound names and paths on the warehouse, the probes' own schema, and what the probe app's secret resource grants.
- Ticket 04, steps 1 to 4: deploy the bundle twice, run the nightly job by hand, compare the sample queries on DuckDB and the SQL warehouse, and record both nightly schedules.
- Ticket 08, steps 1 and 2: read P156634's Procurement Plans on the warehouse twice on the same day, then compare the plan's queries on DuckDB and the SQL warehouse.

## Blocked

- Ticket 06 is blocked by 02. Its other blockers, 03 and 04, are satisfied.
- Ticket 09 is blocked by 07. Its other blocker, 08, is done.
- Ticket 17 is blocked by 07.
- Ticket 10 is blocked by 06 and 09, and ticket 11 by 09.
- Ticket 12 is blocked by 07 and 10, ticket 13 by 11, ticket 14 by 10 and 13, ticket 15 by 12 and 14, and ticket 16 by 06, 07 and 11.
- The other 32 open tickets, 18 to 49, wait on tickets that are themselves blocked. Each ticket's `Blocked by` line names its blockers.
- On the user: P0's exit criterion, ticket 03's criteria 2 to 5, ticket 04's criteria 1, 2, 3, 4 and 7, ticket 08's three live checks, and every live step that later tickets park all wait for `.env`.

## Dates

Today is Friday, October 23, 2026, which is day 1 of about 15, counting October 22 as day 0.

- **October 31, 2026, 8 days left.** P156634, the project behind the demo plan, closes, as `docs/PLAN.md` sections 3 and 16 say. `data/fixture/README.md`, under "Before demo day", gives the recheck steps for two plan rows that the awards dataset contradicts.
  - KE-NWWDA-541055-CW-RFB. The October 9 plan shows no signed contract. The awards dataset shows contract 1903781, signed on June 22, 2026 for US$1,287,515.60, and award notice OP00474946 was published on October 13, 2026. Ticket 08's verification read the plan row's planned Contract Completion of 2026-07-31 with no actual signing date.
  - KE-NWWDA-541062-CW-RFQ. The plan says Pending Implementation. The awards dataset shows contract 1903551, signed on May 11, 2026.
  - On demo day, run `uv run python -m strata.fixture.record`. It prints a diff and writes nothing until you run it again with `--write`. Then run the gate, which checks every value in `tests/ground_truth/values.toml` against the recorded files.
  - Recheck both rows' signals. If one of the four comparables still open was signed or canceled, move it in `values.toml` and update the counts. If fewer than three stay open, record another Kenya works package under Request for Bids that was still open on the plan's date.
  - Then settle decision 7, the story the demo leads with. P130164 stays the closed showcase.
- **About November 6, 2026, 14 days left.** Round 2 of the interview, where the panel asks for live code changes (`docs/PLAN.md` section 1). The repo says only "about 15 days from October 22", so the real date may differ. See decision 4.
- **November 10, 2026, 18 days left.** The Azure free credit ends, so the subscription moves to pay-as-you-go before then, as `docs/PLAN.md` section 2 says. `docs/day-one-results.md` says "Not done yet". Ticket 03's verification found that the wizard refuses any pay-as-you-go date on or after November 10. See decision 2.

The schedule check runs on the tickets' `Blocked by` lines and counts build rounds. One build round is the time one ticket takes from dispatch to merge. With four tickets at once and the longest chain first, the 44 open tickets need 13 build rounds, and P1's last ticket, 15, merges in round 6. With three at once they need 15 rounds. At the measured 2 hours 14 minutes a ticket, 13 rounds come to about 29 hours of build time. That pace comes from six tickets that merged. Ticket 02 has been open for 6 hours 26 minutes, P2's tickets are larger, and the build pauses whenever a session ends, so the real pace is slower. `docs/PLAN.md` section 13 gives no day count for each phase. No phase is over the time the round count gives it, so nothing moves to "designed, not built" yet.

## Risks

**From `docs/PLAN.md` section 16**

- **Free Edition cannot reach the World Bank hosts.** This is day-one test 1, and `docs/day-one-results.md` says "not run". Tickets 07 and 08 fetch from these hosts in their live runs, so both live runs wait on it. The owner is ticket 03, run by the user. Next step: `bash ops/dayone/run-probes.sh --env-file .env` runs the test 1 probe from a notebook, a job and the app. If it fails, ingestion moves to a Container Apps job that pushes files into the volume.
- **The daily quota stops compute during a review.** Nothing runs on the workspace yet. Ticket 08 parses each page once, and its verification found that a second run parsed 0 pages. Ticket 04 set the nightly job to 05:00 New York time in `bundle/nightly.yml`. The owner is the orchestrator after the wizard, then ticket 43. Next step: catch-up step 4 for ticket 04 records both nightly schedules in `bundle/README.md`, and its Overlap line must start with "- Overlap: none".
- **The app stops 24 hours after each deploy.** The owner is ticket 48. Next step: ticket 06 deploys the first app, which is where the stop first shows up. Ticket 48's demo-ready command restarts and warms it, in P4.
- **The free credit ends on November 10.** 18 days are left, and pay-as-you-go is "Not done yet". The owner is the user. Next step: decision 2.
- **Prompt Shields refuses real report text.** The owners are tickets 11 and 13. Next step: ticket 11 stores a Prompt Shields result for every passage, and ticket 13 sends real passages with rule-like sentences through the live agent. Both live checks need Foundry, so they wait for the wizard.
- **Supplier names are matched wrongly.** The owner is ticket 19, which starts after ticket 17. On ticket 07's branch, gold already joins a joint venture's members on their supplier IDs, with each amount counted once (`.notes/07-verify-r4.md`, criterion 4). Next step: ticket 19 matches on IDs first and sends uncertain matches to a person, which needs the labeling time in decision 5.
- **The demo plan's project closes October 31.** That is 8 days away. The owner is the user on demo day, with ticket 05's fixture. Next step: the recheck steps under October 31 in "Dates".
- **"Build complete" outruns the time.** 44 tickets are open and 14 days are left to the assumed Round 2 date. The schedule check needs 13 build rounds. The owner is the PM with the orchestrator. Next step: measure the pace again at the P1 gate. If a phase runs over, tickets 43 and 44 move to "designed, not built" first, because Operationalization carries 15 points, the lowest weight in `docs/PLAN.md` section 17. That brings 13 rounds down to 12. See decision 6.

**New since planning**

- **Ticket 07 sits on the longest chain and failed one criterion.** Every extra build round it takes moves the end by one round. The owner is the orchestrator. Next step: send round 5 to the same worktree with the verifier's four-step fix for criterion 3 and review polish P1's seven phone labels, then verify again and merge.
- **A flaky test could enter the gate with ticket 02.** Review round 7 found that the tab tests fail about once in 30 gate runs. If 02 merges as it is, that failure would stop unrelated commits overnight. The owner is the orchestrator with design-lead. Next step: apply the four-line `fontsSettled` fix from `.notes/02-review-r7.md`, merge `build/strata` into the branch, run the verifier, then merge and run the P0 phase gate.
- **Live steps keep piling up while `.env` is missing.** Ten blocks wait in `docs/workspace-catchup.md`. Nine criteria are parked (ticket 03's 2 to 5 and ticket 04's 1, 2, 3, 4 and 7), plus ticket 08's three live checks, and ticket 07 will park one more. A live run may show failures that the offline versions hid. The owner is the user for the wizard, then the orchestrator for the catch-up. Next step: decision 1, then run the blocks in order and have the verifier re-check each parked item.
- **Only one layout parser is built.** `config/models.toml` names `ai_parse_document`, and ticket 08's tests use output written by hand in its version 2.0 shape. Day-one test 3 has not run. If it fails, a Content Understanding adapter must join `PARSERS` in `src/strata/reader/layout.py` (`.notes/08-verify-r2.md`, parked item 3). The owner is the orchestrator after the user's probes. Next step: catch-up step 1 for ticket 08 proves the real shape.
- **The live notices may hold phone numbers the stripper misses.** CLAUDE.md rule 8 says notice contact details are stripped at ingestion. Ticket 07's review found seven common label shapes, such as `Telephone Number:` and `Cellphone:`, that the label pass does not know. No recorded notice uses them, so the offline scan passes, but the live run reads every Kenya notice. The owner is ticket 07's builder. Next step: add the seven labels in round 5, with the review's test patterns.
- **The gate's Python lane is growing.** The Python tests set the gate's total, at 31.2 of 33.4 seconds at 09:21. Ticket 07's branch already took 48.0 seconds in its verification. Ticket 50's merger comment says this step needs pytest-xdist workers as `tests/` grows, as `docs/agents/areas/ops.md` says. The owner is the orchestrator. Next step: give the Python lane's pytest step workers, as the ops lane has, before the gate passes 60 seconds on `build/strata`.
- **The secret scan does not read the incoming branch during a merge.** Ticket 01's verification found this as V1. The mergers for 50 and 08 scanned each branch by hand first, as their merger comments say. The owner is the merger, through its step 3 in `.claude/agents/merger.md`. Next step: keep the hand scan on every merge. The PM proposes a ticket to have the gate scan the incoming branch itself.
- **Review polish has no ticket to land in.** The merger comments list open polish for ticket 01 (V1, P1, P2 and P3), ticket 03 (P1 and N5), ticket 04 (P1 to P4), ticket 05 (P1 to P3), ticket 50 (P1 and P2) and ticket 08 (S2 to S6, and verification findings F1 to F3). The owner is the orchestrator with the PM. Next step: copy 08's F2 into ticket 09's notes and its F3 and S5 into ticket 16's notes before those waves. The PM proposes one new ticket for the rest, with no ticket waiting on it, so it never holds up the chain.
- **`docs/PLAN.md` names four loan-number forms, and the data has a fifth.** Section 3 lists `IDA60290`, `IDA-60290`, `60290` and `IDA / 60300`. Ticket 07's verification found `6030-KE` in 49 notices. CLAUDE.md rule 4 keeps each definition in one place. The owner is the orchestrator. Next step: add the fifth form to section 3 in the same change as 07's fix, as the verifier suggests.
- **fairshare cannot be read.** Listing its folder failed with "Operation not permitted" at 09:20 on October 23. Tickets 01, 02 and 04 wrote their fairshare parts from `docs/PLAN.md` section 12 and the spec. Tickets 06, 13, 33 and 35 also name fairshare code to copy or adapt, and ticket 43 needs fairshare's nightly schedule. The owner is the user for access, and the orchestrator until then. Next step: decision 3.
- **One set of SQL runs on two engines.** Ticket 04's sample queries pass on DuckDB. Ticket 08 checks its plan's ground-truth files on both engines through the bundle check (commit 016676e). The warehouse side is catch-up step 3 for ticket 04 and step 2 for ticket 08. The owner is the orchestrator. Next step: run both after the wizard.

Two earlier claims are corrected. `core.hooksPath` is the relative path `.githooks`, which `git config --get core.hooksPath` printed at 09:18, so it was never absolute. `.env.example` lists 10 keys, not 15, since ticket 04 removed `STRATA_CATALOG` and the four `STRATA_MODEL_*` keys.

## Decisions for the user

Each decision says what the build does until you answer.

**First thing in the morning**

1. **Run the wizard and the probes.** This is a step rather than a choice, but P0 cannot close without it. From the main checkout, run `bash ops/wizard/strata-setup.sh`, then `bash ops/dayone/run-probes.sh --env-file .env`, then `bash ops/wizard/strata-setup.sh` once more to finish test 6. After that, the orchestrator runs the ten blocks in `docs/workspace-catchup.md` in order. Until then, every live step waits there.
2. **Pay-as-you-go before November 10.** The wizard's pay-as-you-go stage accepts only a date before November 10. Until you do it, `docs/day-one-results.md` says "Not done yet" for pay-as-you-go, and the build keeps spending the free credit.
3. **fairshare access.** Either grant access so the build can compare its code with fairshare's, or accept the rewrite from `docs/PLAN.md` section 12. Until you answer, the build writes the code from the description.
4. **The exact date of Round 2.** The repo says only "about 15 days from October 22". Until you answer, the PM counts to November 6.

**Within about a week**

5. **Labeling time.** Ticket 19 needs about 1,000 supplier pairs labeled, ticket 32 about 150 notice queries judged by two people, and ticket 34 the risks that completion reports blamed, coded by two people. Decide how much you will label, who the second person is, or whether model-drafted labels that you spot-check are acceptable if the proposal says so. Until you answer, the tickets build the labeling tools and report whatever has been labeled.
6. **What gives way first if time runs short.** Nothing needs to give way now. If it does, the PM proposes the lowest rubric weight first. Tickets 43 and 44, Operationalization at 15 points, move to "designed, not built", and ticket 45 shrinks to the one dashboard page that ticket 16 builds. That saves one build round of 13. Domain alignment comes next, mainly tickets 35 to 42. Until you answer, nothing is cut.
7. **The demo story for KE-NWWDA-541055-CW-RFB.** The October 9 plan shows no signed contract, while the awards dataset shows one signed on June 22, 2026. Decide whether the demo leads with "no signed contract" or shows the plan and the award row disagreeing. Until you answer, `tests/ground_truth/values.toml` keeps the plan's own values and records the award rows beside them.
8. **Ticket 08's four choices.** They are in ticket 08's merger comment and in `.notes/08-verify-r2.md`. A delay whose first listing could not be confirmed is kept and marked with `first_listing_confirmed` false. The October 9 plan lists nine activities, one more than the wireframe's eight. Words that wrap in a description stay split as the PDF gives them. A delay row takes the later of its two plans' public dates, a one-line change before ticket 09 reads it. Until you answer, the build follows these picks.

**From the design briefs**

9. **The briefs' parked choices.** `.notes/parked-decisions.md` lists every choice the design briefs settled so building could go on, in a P1 batch for tickets 06, 10, 12, 14, 15 and 16, then P2 and P3 batches. Until you answer, the build follows each brief. The ones you will see first are on the app shell and Check a plan.
   - The navy bar marks the selected tab with a white underline and shows keyboard focus in orange, because DESIGN.md's primary and focus colors are too faint on navy (ticket 06, written into DESIGN.md by ticket 02).
   - The tabs fold into a Menu button below 1024 px, not below 768 px (ticket 06).
   - Check a plan quotes STEP amounts to the cent, which departs from DESIGN.md rule 11's rounded style, so the figure matches STEP (ticket 10).
   - Check a plan adds two routes for a plan version that `docs/PLAN.md` section 8 does not list (ticket 10).

**Whenever you get to them**

10. **The GitHub repo.** Decide which account owns it when it is first pushed. Creating the repo and adding reviewers is your step. Until you answer, nothing is pushed, under CLAUDE.md rule 10.
11. **Git identity.** Commits in this repo are authored as "Chirag Lakhanpal <chirag.lakhanpal.cl@gmail.com>", set in this repo's git config. Say if you want a different name or email. A change affects only new commits. Until you answer, nothing changes.
12. **The "About this demo" page.** Decide whether the footer gets a page that lists the proposal, the dashboard, the repo and the deck with its speaker notes. Brief 06 left the footer with only the DESIGN.md section 8 sentence. Until you answer, the page stays unbuilt, as the spec says, and the deck stays at `/present` with no link.
