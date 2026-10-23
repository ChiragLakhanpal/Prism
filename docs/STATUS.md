# Strata build status

_Kept current by the `pm` agent. Last updated at 06:16 Pacific time on Friday, October 23, 2026, from commit 5a0fa3a on `build/strata`._

## Today

Four tickets reached `build/strata` between 00:04 and 06:04 on October 23. Ticket 01 merged at 45a8298, ticket 05 at f961131 and ticket 04 at 01a7286. Ticket 03 landed as squash commit 43ed569 and is now `ready-for-human`. From dispatch to merge they took 1 hour 46 minutes, 3 hours 32 minutes, 2 hours 30 minutes and 2 hours 23 minutes, which averages 2 hours 33 minutes a ticket. Phase P0 is not closed. Ticket 02 is still open after four review rounds, so the P0 phase gate did not run, and P0's exit criterion needs day-one test results that only the user can produce. The file `.env` is still missing, and all 10 keys that `.env.example` lists are unset (`python3 .claude/hooks/guard.py --env-keys` at 06:11). The list shrank from 15 keys to 10 in commit fae9dc0, which moved the four model names into `config/models.toml`. Eight workspace steps now wait in `docs/workspace-catchup.md`, four from ticket 03 and four from ticket 04, and nine acceptance criteria are parked behind them. The next wave is tickets 07 and 08, the only two tickets whose blockers are all done, running beside 02 and 50. At the measured pace the offline build fits the calendar with days to spare. The dates now depend on the user's wizard, because P0's exit, P1's deployed app and every parked criterion need the shared workspace.

## Phase

P0 Foundations, from `docs/PLAN.md` section 13. Its tickets are 01 to 05. Across the plan, the tickets' Phase lines count 5 tickets in P0, 12 in P1, 29 in P2, 2 in P3 and 2 in P4, which makes 50. Ticket 50, the gate lanes, is new since the last status. Commit 5bfaaae opened it.

Exit criterion:

- [ ] Every day-one test has a result and a chosen path. Not met. `docs/day-one-results.md` lists all ten tests from `docs/PLAN.md` section 14, and every one says "not run". Ticket 03's second criterion says the user fills it by running the wizard and the probes.

The phase's work, as `docs/PLAN.md` section 13 lists it:

- [x] The repo with its rules, hooks and gate. Ticket 01 merged at 45a8298, and round 3's verification passed all 9 criteria, in `.notes/01-verify-r3.md`.
- [ ] The `strata` catalog. Ticket 04 merged its offline half at 01a7286. The catalog does not exist on the workspace yet. Round 3's verification passed criteria 5 and 6 and parked criteria 1, 2, 3, 4 and 7, in `.notes/04-verify-r3.md`.
- [ ] The day-one tests, the model deployments, the Azure caps and pay-as-you-go before November 10. Ticket 03's wizard and probes landed at 43ed569. Round 5's verification passed criterion 1 and parked criteria 2 to 5, in `.notes/03-verify-r5.md`. `docs/day-one-results.md` says "Not done yet" for pay-as-you-go and "not checked" for the caps.
- [ ] The design-system foundation, ticket 02. It is in progress with one blocking finding from review round 4 and one from critique round 4.
- [x] The demo and showcase fixtures, ticket 05. It merged at f961131, and round 3's verification passed all 7 criteria, in `.notes/05-verify-r3.md`.

The P0 phase gate runs when ticket 02 merges, and it can pass only after the user's wizard and probes. P1 ends when the deployed app checks one plan and answers one question with citations, and the offline gate runs in under two minutes. The deployed app needs the workspace and Foundry, so offline work alone cannot meet P1's exit either.

## Frontier

The frontier is every `ready-for-agent` ticket whose blockers are all `done`, with ticket 03 counted as satisfied. The ticket with the longest chain of tickets waiting on it goes first, and the lowest number breaks ties. Both rules are in the standing rules of `docs/agents/build.md` and in `docs/agents/issue-tracker.md`.

1. Ticket 07, Kenya's procurement records. Its blockers, 04 and 05, are done. 41 tickets wait on it, and its longest chain is 13 tickets.
2. Ticket 08, P156634's Procurement Plans as STEP rows. Its blockers, 04 and 05, are done. 39 tickets wait on it, and its longest chain is 13 tickets.

With 02 and 50 still in flight, that makes four tickets running at once. Neither 07 nor 08 adds a screen, so neither needs a brief. Every ticket from 06 to 47 that has `Design review: yes` already has a brief in `.notes/`, so no brief is owed before a later wave. Ticket 06 joins the frontier when 02 merges, and ticket 09 when both 07 and 08 merge.

What the next builders need from the reviews:

- Ticket 07 adds the first new table, so it meets ticket 04's review polish P2 first. `tests/test_catalog.py:148` pins the list of table definitions to `["strata.ops.pipeline_runs"]`, and the first new table turns it red. Polish P1 in the same review says `check_public_from` skips every schema the bundle does not declare. Both are in `.notes/04-review-r3.md`.
- Ticket 06 deploys the first app. Ticket 01's verification asks that ticket to check that `GET /api/me` inside the deployed app names the viewer and returns `"has_token": true`, never the token. The request is in ticket 01's merger comment.
- `.notes/later-wave-notes.md` holds lines for tickets 12, 15, 23, 26, 27, 38, 41 and 45. The orchestrator copies each into its ticket's notes when that wave starts.

## In flight

| Ticket | Branch and worktree | In progress since | Where it stands |
|---|---|---|---|
| 02, the design-system foundation | `strata/02-design-system-foundation` in `.claude/worktrees/wf_3754dbdb-163-2`, tip de873fa from 05:07 | 02:55 on October 23, commit e48667e | Review round 4 asks for changes with one blocking finding. The citation marker test measures the word joiner, so it can never fail, and the review gives a two-line fix. Critique round 4 scores the tabs on a light surface 3 for alignment, because the five tabs wrap onto two rows at 390 px. It blocks the merge until that is fixed or design-lead records why it stands. No verifier result exists yet. The orchestrator holds the next step. |
| 50, gate lanes | `strata/50-gate-lanes` in `.claude/worktrees/wf_384e6421-3b6-1`, tip 2f575cc from 05:48 | 05:18 on October 23, commit 5bfaaae | Review round 1 approves with four polish findings, in `.notes/50-review.md`. The gate passed on the branch in 25.6 and 26.0 seconds. No verifier result exists yet. |

Ticket 03 is `ready-for-human`, so no agent works on it. It waits for the three commands in decision 1.

## Done (this phase)

A ticket counts as done only when its file says `done`, it is merged into `build/strata`, and its verifier result passed.

| Ticket | Status commit | Merge commit | Verification | Proven on the workspace |
|---|---|---|---|---|
| 01, the repo scaffold and offline gate | e686398 | 45a8298 | Round 3 passed 9 of 9 criteria | It has no workspace step |
| 05, the demo and showcase fixtures | 78a65bf | f961131 | Round 3 passed 7 of 7 criteria | It has no workspace step |
| 04, the catalog and bundle skeleton | 5a0fa3a | 01a7286 | Round 3 passed criteria 5 and 6, parked 1, 2, 3, 4 and 7, and failed none | Not yet. Catch-up steps 1 to 4 for ticket 04 must run first |

Ticket 04 counts as done for the frontier. Its five parked criteria stay unproven until the catch-up runs and the verifier re-checks them.

Ticket 03 is not done. Its file says `ready-for-human`, set in commit 79a3ab3, and its criteria 2 to 5 are parked.

After ticket 04's merge, the gate on `build/strata` passed in 74.1 seconds at 06:07, and the Python tests took 65.1 seconds of that. The figures are in ticket 04's merger comment.

Parked live checks, from `docs/workspace-catchup.md`:

- Ticket 03, steps 1 to 4: the unit of a Global Batch capacity, bound names and paths on the warehouse, the probes' own schema, and what the probe app's secret resource grants.
- Ticket 04, steps 1 to 4: deploy the bundle twice, run the nightly job by hand, compare the sample queries on DuckDB and the SQL warehouse, and record both nightly schedules.

## Blocked

- Ticket 06 is blocked by 02. Its other two blockers, 03 and 04, are satisfied.
- Ticket 09 is blocked by 07 and 08.
- Ticket 10 is blocked by 06 and 09, ticket 11 by 09, and ticket 17 by 07.
- The other 37 open tickets, 12 to 16 and 18 to 49, wait on tickets that are themselves blocked. Each ticket's `Blocked by` line names its blockers. The longest chain left is 13 tickets: 07, 09, 11, 13, 14, 15, 30, 34, 44, 45, 46, 47 and 49. The chain through ticket 02 is 12 tickets: 02, 06, 10, 12, 15, 30, 34, 44, 45, 46, 47 and 49.
- On the user: P0's exit criterion, ticket 03's criteria 2 to 5, ticket 04's criteria 1, 2, 3, 4 and 7, and every live step that later tickets park all wait for `.env`.

## Dates

Today is Friday, October 23, 2026, which is day 1 of about 15, counting October 22 as day 0.

- **October 31, 2026, 8 days left.** P156634, the project behind the demo plan, closes, as `docs/PLAN.md` sections 3 and 16 say.
- **About November 6, 2026, 14 days left.** Round 2 of the interview, where the panel asks for live code changes. The repo says only "about 15 days from October 22", so the real date may differ.
- **November 10, 2026, 18 days left.** The Azure free credit ends, so the subscription moves to pay-as-you-go before then, as `docs/PLAN.md` section 2 says. `docs/day-one-results.md` says "Not done yet". Ticket 03's verification found that the wizard refuses any pay-as-you-go date on or after November 10.

The schedule check runs on the tickets' `Blocked by` lines and counts rounds, where one round is the time one ticket takes from dispatch to merge. With four tickets at once and the longest chain first, the 46 open tickets need 13 rounds, and P1's last ticket merges in round 6. With three at once they need 16 rounds. The last status assumed one day a round and found no spare day. The four merged tickets averaged 2 hours 33 minutes, so 13 rounds come to about 33 hours of build time at that pace. That figure comes from four P0 tickets only. P2's tickets are larger, and the build pauses whenever a session ends.

## Risks

**From `docs/PLAN.md` section 16**

- **Free Edition cannot reach the World Bank hosts.** This is day-one test 1, and `docs/day-one-results.md` says "not run". Ticket 05's recording command reached every source from this computer, which says nothing about the workspace. The owner is ticket 03, run by the user. Next step: `bash ops/dayone/run-probes.sh --env-file .env` runs the test 1 probe from a notebook, a job and the app. If it fails, ingestion moves to a Container Apps job that pushes files into the volume.
- **The daily quota stops compute during a review.** Nothing runs on the workspace yet. Ticket 04 set Strata's nightly job to 05:00 New York time in `bundle/nightly.yml`, but the check against fairshare's job is catch-up step 4 for ticket 04. The owner is the orchestrator after the wizard, then ticket 43. Next step: once fairshare's job has finished one run, `uv run --script ops/bundle/check.py schedules --env-file .env --write` records both jobs in `bundle/README.md` and must show "- Overlap: none".
- **The app stops 24 hours after each deploy.** The owner is ticket 48. Next step: ticket 06 deploys the first app, which is where the stop first shows up. Ticket 48's demo-ready command restarts and warms it, in P4.
- **The free credit ends on November 10.** 18 days are left, and `docs/day-one-results.md` says pay-as-you-go is "Not done yet". The owner is the user. Next step: the wizard's pay-as-you-go stage, which accepts only a date before November 10.
- **Prompt Shields refuses real report text.** The owners are tickets 11 and 13. Next step: ticket 11 stores a Prompt Shields result for every passage, and ticket 13 sends real passages with rule-like sentences through the live agent. Both live checks need Foundry, so they wait for the wizard.
- **Supplier names are matched wrongly.** The owner is ticket 19, which starts after ticket 17. IDs decide first, there are no supplier scores, and a person decides the uncertain matches, which needs the labeling time in decision 5.
- **The demo plan's project closes October 31.** That is 8 days away. The owner is the user on demo day, with ticket 05's fixture. `data/fixture/README.md`, under "Before demo day", names two plan rows that the awards dataset contradicts. KE-NWWDA-541055-CW-RFB shows no signed contract in the plan, while the awards dataset shows contract 1903781 signed on June 22, 2026 for US$1,287,515.60 and award notice OP00474946 published on October 13, 2026. KE-NWWDA-541062-CW-RFQ says Pending Implementation in the plan, while contract 1903551 was signed on May 11, 2026. Bids for two of the four comparables still open were due on October 13 and October 21, 2026, according to ticket 05's merger comment, so a refresh may turn the comparable test red. Next step: on demo day, run `uv run python -m strata.fixture.record`, then the gate. Move any comparable that was signed or canceled in `tests/ground_truth/values.toml`, recheck both rows' signals, and settle decision 6. P130164 stays the closed showcase.
- **"Build complete" outruns the time.** 46 tickets are open and 14 days are left. The schedule check above needs 13 rounds, and at the measured 2 hours 33 minutes a round that leaves room. The owner is the PM with the orchestrator. Next step: measure the pace again at the P1 gate, when P1's larger tickets have merged. No cut is needed now. If a phase runs over its share, the first cut stays tickets 43 and 44, Operationalization at 15 points, the lowest rubric weight in `docs/PLAN.md` section 17. Moving both to "designed, not built" brings 13 rounds down to 12. See decision 5.

**New since planning**

- **Live steps keep piling up while `.env` is missing.** Eight blocks wait in `docs/workspace-catchup.md`, and nine criteria are parked: ticket 03's criteria 2 to 5 and ticket 04's criteria 1, 2, 3, 4 and 7. Ticket 06 deploys the app, so from P1 on the parked work includes the deployed app that P1's exit criterion names. A live run may show failures that the offline versions hid, and a failed day-one test could change a path that tickets were built on. The owner is the user for the wizard, then the orchestrator for the catch-up. Next step: decision 1, then run the catch-up blocks in order and have the verifier re-check each parked criterion.
- **Ticket 02 has taken four rounds, and 37 tickets wait on it.** Its chain is 12 tickets, one shorter than the chain through 07. If 02 takes two more rounds, the chain through 06 becomes the longest and pushes the end date. The owner is the orchestrator with design-lead. Next step: send the two-line fix from `.notes/02-review-r4.md` and have design-lead either give light-surface tabs a rule for phone widths or record in DESIGN.md why the wrap stands. Then run the verifier and merge.
- **The gate is close to its two-minute limit.** It took 74.1 seconds on `build/strata` at 06:07. Ticket 50's description says tickets 02, 04 and 05 each add 10 to 15 seconds, and every P1 ticket adds tests on top. Ticket 50's branch runs it in 25.6 to 26.0 seconds. The owner is the orchestrator. Next step: verify ticket 50 and merge it before 07 or 08 merges, as ticket 50's comment asks.
- **The secret scan does not read the incoming branch during a merge.** Ticket 01's verification found this as V1. The mergers for 01, 03, 04 and 05 covered it by scanning the branch by hand first, and that scan is why ticket 03 landed as a squash. The owner is the merger, through its step 3 in `.claude/agents/merger.md`. Next step: keep the hand scan on every merge. The PM proposes a ticket to have the gate scan the incoming branch itself.
- **Review polish has no ticket to land in.** The merger comments list open polish for ticket 01 (V1, P1, P2 and P3), ticket 03 (P1 and N5), ticket 04 (P1 to P4) and ticket 05 (P1 to P3). Unless a ticket holds these items, they get lost. The owner is the orchestrator with the PM. Next step: copy 04's P1 and P2 into ticket 07's notes now. The PM proposes one new ticket for the rest, with no ticket waiting on it, so it never holds up the chain.
- **fairshare cannot be read.** Listing its folder failed with "Operation not permitted" at 06:13 on October 23. Tickets 01, 02 and 04 wrote their fairshare parts from `docs/PLAN.md` section 12 and the spec. The docstring of `src/strata/dbx.py` says so for 01, `.notes/02-review-r4.md` says so for 02, and ticket 04's merger comment says so for 04. Tickets 06, 13, 33 and 35 also name fairshare code to copy or adapt, and ticket 43 needs fairshare's nightly schedule. The owner is the user for access, and the orchestrator until then. Next step: decision 2.
- **One set of SQL runs on two engines.** Ticket 04 landed the engine adapter, and both sample queries pass on DuckDB, according to `.notes/04-verify-r3.md`. The same queries on the SQL warehouse are catch-up step 3 for ticket 04. The owner is the orchestrator. Next step: run that step after the wizard, and revisit the approach if Lakeflow features get in the way.

Two risks from the last status are closed. `core.hooksPath` is the relative path `.githooks`, which `git config --get core.hooksPath` printed at 06:11 and which line 8 of `.git/config` stores, so the hooks-path risk was a misreading and is dropped. The pick order is now longest chain first, recorded in the standing rules of `docs/agents/build.md` and in `docs/agents/issue-tracker.md`.

## Decisions for the user

Each decision says what the build does until you answer.

**First thing in the morning**

1. **Run the wizard and the probes.** This is a step rather than a choice, but P0 cannot close without it. From the main checkout, run `bash ops/wizard/strata-setup.sh`, then `bash ops/dayone/run-probes.sh --env-file .env`, then `bash ops/wizard/strata-setup.sh` once more to finish test 6. After that, the orchestrator runs the blocks in `docs/workspace-catchup.md` in order. Until then, every live step waits there.
2. **fairshare access.** Either grant access so the build can compare its code with fairshare's, or accept the rewrite from `docs/PLAN.md` section 12. Until you answer, the build writes the code from the description.
3. **The exact date of Round 2.** The repo says only "about 15 days from October 22". Until you answer, the PM counts to November 6.

**Within about a week**

4. **Labeling time.** Ticket 19 needs about 1,000 supplier pairs labeled, ticket 32 about 150 notice queries judged by two people, and ticket 34 the risks that completion reports blamed, coded by two people. Decide how much you will label, who the second person is, or whether model-drafted labels that you spot-check are acceptable if the proposal says so. Until you answer, the tickets build the labeling tools and report whatever has been labeled.
5. **What gives way first if time runs short.** At the measured pace nothing needs to give way now. If it does, the PM proposes the lowest rubric weight first. Tickets 43 and 44, Operationalization at 15 points, move to "designed, not built", and ticket 45 shrinks to the one dashboard page that ticket 16 builds. That saves one round of 13. Domain alignment comes next, mainly tickets 35 to 42. Until you answer, nothing is cut.
6. **The demo story for KE-NWWDA-541055-CW-RFB.** The October 9 plan shows no signed contract, while the awards dataset shows one signed on June 22, 2026. Decide whether the demo leads with "no signed contract" or shows the plan and the award row disagreeing. Until you answer, `tests/ground_truth/values.toml` keeps the plan's own values and records the award rows beside them, as it does now.

**From the design briefs for tickets 06, 10, 12, 14, 15 and 16**

`.notes/parked-decisions.md` lists 76 choices from these six briefs. The briefs settled them so building could go on. The ones below change `DESIGN.md`, `GLOSSARY.md` or `docs/PLAN.md`, or the brief asked you to confirm them. Until you answer, the build follows each brief.

7. **Ticket 06, the navy bar.** The selected tab gets a white underline and keyboard focus uses #f5926c, because DESIGN.md's primary measures 1.55:1 and its focus color 3.01:1 on navy, and ticket 02 writes both into DESIGN.md.
8. **Ticket 06, additions to DESIGN.md.** Ticket 02 adds a highlight token, #fff1b8, from brief 14, an empty-state card, the Partial and Gap badges from brief 16, and a Menu below 1024 px rather than below 768 px.
9. **Ticket 10, amounts to the cent.** Reasons quote STEP amounts such as "US$1,245,092.76" so they match STEP, which departs from DESIGN.md rule 11's "US$12.5 million" style.
10. **Ticket 10, two new routes.** A plan version opens at `/projects/:pid/procurement/:agencyId/:version`, and the latest plan at the same path without the version, though neither route is in `docs/PLAN.md` section 8.
11. **Ticket 12, the 8-in-10 point.** The chart names the Kaplan-Meier value without "31 of 37" beside it, because open packages can make the raw count disagree, which is a reading of DESIGN.md rule 15 that the brief asks you to confirm.
12. **Ticket 15, chip words.** Chips show the blueprint's sentence-case words such as "Open international", while the editor and the drawer use STEP's field names word for word, which is how the brief reconciles DESIGN.md rule 17 with the blueprint's Words table.
13. **Ticket 15, group labels.** The form's groups are labeled What, Where and How, and two of those words are GLOSSARY.md stratum names with a different meaning.
14. **Ticket 16, Partial thresholds.** A source shows Partial below 90 percent linked or read well, or more than one day past its update schedule, with both values in the thresholds file.
15. **Ticket 16, the dashboard's two departures.** Chart titles name what they measure rather than the finding, and the dashboard uses AI/BI's own font, so DESIGN.md needs a line for each.

The later briefs, for tickets 18 to 47, parked 614 more choices in the same file. The PM folds in the ones that need you as their tickets near the frontier.

**Whenever you get to them**

16. **Git identity.** Commits in this repo are authored as "Chirag Lakhanpal <chirag.lakhanpal.cl@gmail.com>", set in this repo's `.git/config`. Say if you want a different name or email. A change affects only new commits. Until you answer, nothing changes.
17. **The GitHub repo.** Decide which account owns it when it is first pushed. Creating the repo and adding reviewers is your step. Until you answer, nothing is pushed, under `CLAUDE.md` rule 10.
18. **The "About this demo" page.** Decide whether the footer gets a page that lists the proposal, the dashboard, the repo and the deck with its speaker notes. Brief 06 left the footer with only the DESIGN.md section 8 sentence. Until you answer, the page stays unbuilt, as the spec says, and the deck stays at `/present` with no link.
