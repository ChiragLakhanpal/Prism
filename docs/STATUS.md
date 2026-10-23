# Strata build status

_Kept current by the `pm` agent. Last updated at 16:10 Pacific time on Friday, October 23, 2026, from commit 0fbdb58 on `build/strata`. Wave 3c was still running when I read the repo, so tickets 06, 13 and 17 may have moved since._

## Today

Five more tickets reached `build/strata` since the last status at 09:25. Wave 3b merged ticket 07, Kenya's procurement records, at dbc054a at 12:51, and ticket 51, the python lane's workers, at b8a818a at 13:14. Wave 3c merged ticket 02, the design-system foundation, at 9f41b42 at 14:01 after 12 rounds, then ticket 09, the tool registry and check_plan, at f9cc969 at 14:16, and ticket 11, the first 20 documents, at e0721da at 16:00. Each one's verification passed, with its live checks parked. That makes 10 of 51 tickets done, and ticket 03 waits on the user. The wave is still running. Ticket 06, the app shell, is in its third round after its round 2 verification failed one criterion. Ticket 13, the cited answer, was dispatched at 16:05 and had no branch at 16:06. Ticket 17, which is P2 work, is in a side run after its round 4 review blocked on a privacy finding. The P0 phase gate ran at 14:14 and failed one check, a missing block in the catch-up file, which the orchestrator added in ca4c6e5 at 14:19. P0's exit criterion is still not met, because all ten day-one tests say "not run". The gate passed in 30.3 seconds on ticket 11's merge commit and in 47.6 seconds by hand right after. The environment file is still missing, and all 10 keys were unset at 16:06. The catch-up file now holds 21 blocks. The schedule check needs 11 more build rounds with four tickets at once, and 14 days are left to the Round 2 date the PM assumes. The offline build is on track. The live half cannot move until the user runs the wizard.

## Phase

P0 Foundations is still open, and P1 Walking skeleton is the phase being built. Both come from `docs/PLAN.md` section 13. The tickets' Phase lines count 5 tickets in P0, 13 in P1, 29 in P2, 2 in P3 and 2 in P4, which makes 51. Tickets 50 and 51 are P1.

### P0 Foundations

Exit criterion:

- [ ] Every day-one test has a result and a chosen path. Not met. At 16:06, `python3 ops/dayone/dayone.py show` printed "not run" for all ten tests, each with its default path, and `grep -c 'None yet. The command above fills it.' docs/day-one-results.md` printed 10. Decision 1 is how it closes.

The P0 phase gate ran at 14:14 on 772f59a and failed one check, as `.notes/phase-P0-verify.md` records. The catch-up file had no block for ticket 03's wizard, probes and pay-as-you-go check. The orchestrator added that block in ca4c6e5 at 14:19, and the P1 phase gate checks the catch-up file again. The phase gate's four gate runs passed in 28.1 to 29.0 seconds, one of them with the network blocked.

The phase's work, from `docs/PLAN.md` section 13 and the tickets marked P0:

- [x] The repo with its rules, hooks and gate. Ticket 01 merged at 45a8298, and round 3's verification passed 9 of 9 criteria.
- [ ] The `strata` catalog. Ticket 04 merged its offline half at 01a7286. Its criteria 1, 2, 3, 4 and 7 stay parked until the bundle is deployed.
- [ ] The day-one tests, the model deployments, the Azure caps and pay-as-you-go before November 10. Ticket 03 is `ready-for-human`, with criteria 2 to 5 parked. At 16:06, `dayone.py show` printed "payg: Not done yet" and "caps: not checked".
- [x] The design-system foundation. Ticket 02 merged at 9f41b42, and round 12's verification passed 11 of 11 criteria with none parked, as `.notes/02-verify-r12.md` records.
- [x] The demo and showcase fixtures. Ticket 05 merged at f961131, and round 3's verification passed 7 of 7 criteria.

### P1 Walking skeleton

Exit criteria:

- [ ] The deployed app checks one plan. Not met. Ticket 09's check_plan works offline. The app shell, ticket 06, is in flight, and the Check a plan screen, ticket 10, waits on it. The deploy is a workspace step.
- [ ] The deployed app answers one question with citations. Not met. Ticket 11's passages work offline. Ticket 13 started at 16:05, and ticket 14 waits on 10 and 13.
- [x] The offline gate runs in under two minutes. It holds. Ticket 11's merger ran the gate in 30.3 seconds on e0721da and in 47.6 seconds by hand on `build/strata` right after. I did not run it this time, because the merger runs the gate in the same checkout and two runs at once would both rebuild `data/out/fixture.duckdb`. The P1 phase gate checks it again.

The phase's work, from `docs/PLAN.md` section 13:

- [x] One country ingested. Ticket 07 merged at dbc054a. Round 6's verification passed 8 of 9 criteria and parked criterion 8, as `.notes/07-verify-r6.md` records.
- [ ] One published plan checked. Ticket 08 reads the plan, and ticket 09's check_plan marks it offline. As of October 22, 2026, it gave 1 Needs a look, 2 Watch, 3 data notes and 3 activities with no mark, as ticket 09's merger comment says. The screen, ticket 10, has not started.
- [x] 20 documents read. Ticket 11 merged at e0721da, with 733 passages on the fixture, as its merger comment says. The live run is parked.
- [ ] Comparables and a past range. Ticket 12 waits on 10.
- [ ] One cited answer through the Foundry agent and the verifier. Ticket 13 is in flight, and ticket 14 waits on it.
- [ ] The Data readiness page and one dashboard page. Ticket 16 waits on 06.
- [ ] The deployed app. Ticket 06 is in flight.

Six of P1's 13 tickets are done: 07, 08, 09, 11, 50 and 51. The P1 phase gate runs when the other seven have merged.

Ticket 51 is enabling work the spec allows, not scope creep, since the spec says "If the screen tests threaten that budget they run in parallel workers". The orchestrator opened it in a61c090 when the python lane set the gate's total. The merger comments for 02, 07, 09, 11 and 51 name no work outside their tickets.

## Frontier

The frontier is every `ready-for-agent` ticket whose blockers are all `done`, with ticket 03 counted as satisfied. The ticket with the longest chain of tickets waiting on it goes first, and the lowest number breaks ties, as the standing rules in `docs/agents/build.md` say. The counts below come from the `Blocked by` lines at 16:06.

No `ready-for-agent` ticket is on the frontier right now. Each one waits on 06, 13 or 17, and all three are in flight.

1. Ticket 06, the app shell. 36 tickets wait on it. Its chain is the longest, at 11 tickets: 06, 10, 12, 15, 30, 34, 44, 45, 46, 47 and 49. Each extra round that 06 takes moves the end of the build by one round.
2. Ticket 17, every structured source. 31 tickets wait on it, and its chain is 10 tickets: 17, 18, 29, 30, 34, 44, 45, 46, 47 and 49.
3. Ticket 13, the cited answer. 27 tickets wait on it, and its chain is 10 tickets: 13, 14, 15, 30, 34, 44, 45, 46, 47 and 49.

When 06 merges, ticket 10 joins first, with 30 waiting and a chain of 10, then ticket 16, with 27 waiting and a chain of 10. When 17 merges, ticket 19 joins, with 6 waiting and a chain of 7. Ticket 14 joins when both 10 and 13 have merged, and ticket 18 when both 16 and 17 have. The schedule check finds only three tickets ready in each of the next three rounds, so a fourth slot stays empty until round 4.

What the next builders need:

- Ticket 10. Ticket 09's merger found that the October 9 plan lists 9 activities, so check_plan leaves 3 with no mark, not the 8 activities and 2 folded packages that ticket 10's text gives. Decision 15 covers that wording. Ticket 02's merger asks for one line in the Table test that expects "1,230,000.00", and notes that an amount the tool sends already formatted is shown as sent. Ticket 08's finding F1, words split as in "Explor atory", is decision 8.
- Ticket 16. Ticket 11's merger picks a reading rule: the latest row for each source, subject and measure of `strata.ops.data_readiness`. Ticket 11's review polish P1 says `contact_details_removed` reads 0 of 0 on every run after the first. Ticket 08's F3 and S5 still apply. Ticket 17's verifier asks ticket 16's verifier to confirm all 11 sources appear once 17 lands. The orchestrator copies these into ticket 16's notes before it starts.
- Ticket 12. Ticket 02's merger asks to move the 20 in `FEWEST_FOR_A_FREQUENCY` into `config/thresholds.toml` and have `web/src/lib/format.ts` read both thresholds from there. `.notes/later-wave-notes.md` holds its signing-date rule.
- Ticket 14. Ticket 02's merger leaves it the gap of about 100 px while an answer streams and the check line's alignment, with the rule it picks recorded in DESIGN.md section 5.
- Ticket 13 already has ticket 09's three agent-facing choices, from commit c1945f2.
- Ticket 06 still owes ticket 01's check inside the deployed app. `GET /api/me` must name the viewer and return `"has_token": true`, never the token. The branch returns `has_token` from `src/strata/server/app.py`, so only the live half is left.
- `.notes/later-wave-notes.md` also holds lines for tickets 15, 23, 26, 27, 38, 41 and 45. The orchestrator copies each into its ticket's notes when that wave starts.

## In flight

Wave 3c, run wf_a03357c8-4f6 in `.notes/pause-state.md`, is still running, and ticket 17 has its own side run. These rows come from the ticket files, the worktrees and the notes between 16:06 and 16:10.

| Ticket | Branch and worktree | In progress since | Where it stands |
|---|---|---|---|
| 06, the app shell | `strata/06-deployed-app-shell` in `.claude/worktrees/wf_a03357c8-4f6-5`, tip 8b449c4 from 16:03 | 14:04, commit 772f59a, so 2 hours 6 minutes at 16:10 | In round 3. Round 2's review found nothing blocking and 5 polish items, design-lead passed it with polish, and the critique's lowest score was 4. Round 2's verification failed the offline half of criterion 6. A reset warehouse connection gave a bare 500 and wrote no usage event, as `.notes/06-verify-r2.md` records. Commit 3d4e208 at 15:56 writes the event whatever the route does. The branch then merged `build/strata` at 8b449c4, so it holds ticket 11. No round 3 notes exist yet. Criteria 1, 2, 4 and 7 and criterion 6's trace half are parked for the workspace. |
| 13, the cited answer through Foundry | `strata/13-cited-answer-through-foundry`, not created yet at 16:06 | 16:05, commit 0fbdb58 | The builder is starting. |
| 17, every structured source, a P2 ticket | `strata/17-structured-sources-everywhere` in `.claude/worktrees/wf_e79cc448-4ec-13`, tip 924944a from 15:58 | 12:56, commit 69476b8, so 3 hours 14 minutes at 16:10 | In a side run outside wave 3c, with at most 6 rounds, as `.notes/pause-state.md` says. Review round 4 blocked on B1. Initials such as "S.A." or "B.V." read as a firm's legal form, so a person's name stayed in the row, as `.notes/17-review-r4.md` records. Commit b414976 reads those forms only at the end of a name or before a comma or bracket. Its next review and verification have no notes yet. Criterion 1, which failed verification round 2, was fixed in round 3, and review round 4 confirms it. Criterion 7 is parked, because the branch projects 1.57 GB at full scale against a 0.5 GB limit. The branch's merge base is c1945f2, so it lacks ticket 11. A trial merge with `git merge-tree` at 16:08 conflicts in `src/strata/config.py`. It merges through a mergeOnly entry at the start of wave 4. |

Ticket 03 is `ready-for-human`, so no agent works on it. It waits for decision 1.

## Done (P0 and P1)

A ticket counts as done only when its file says `done`, it is merged into `build/strata`, and its verifier result passed.

| Ticket | Phase | Status commit | Merge commit | Verification | Proven on the workspace |
|---|---|---|---|---|---|
| 01, the repo scaffold and offline gate | P0 | e686398 | 45a8298 | Round 3 passed 9 of 9 criteria | It has no workspace step |
| 05, the demo and showcase fixtures | P0 | 78a65bf | f961131 | Round 3 passed 7 of 7 criteria | It has no workspace step |
| 04, the catalog and bundle skeleton | P0 | 5a0fa3a | 01a7286 | Round 3 passed criteria 5 and 6, parked 1, 2, 3, 4 and 7, and failed none | Not yet. Catch-up steps 1 to 4 for ticket 04 |
| 50, gate lanes | P1 | 9c42e69 | 1c6aa51 | Round 3 passed 8 of 8 criteria, with none parked | It has no workspace step |
| 08, P156634's plans as STEP rows | P1 | 4b5e54f | eba87ed | Round 2 passed 6 of 6 criteria on the fixture and parked three live checks | Not yet. Catch-up steps 1 and 2 for ticket 08 |
| 07, Kenya's procurement records | P1 | 69476b8 | dbc054a | Round 6 passed 8 of 9 criteria and parked criterion 8, in `.notes/07-verify-r6.md` | Not yet. Catch-up steps 1 to 3 for ticket 07 |
| 51, python lane workers | P1 | 9c55652 | b8a818a | Round 2 passed 5 of 5 criteria, with none parked, in `.notes/51-verify-r2.md` | It has no workspace step |
| 02, the design-system foundation | P0 | 772f59a | 9f41b42 | Round 12 passed 11 of 11 criteria, with none parked, in `.notes/02-verify-r12.md` | It has no workspace step |
| 09, the tool registry and check_plan | P1 | c1d63c2 | f9cc969 | Round 2 passed all 7 criteria offline and parked criterion 6's live half, in `.notes/09-verify-r2.md` | Not yet. Catch-up steps 1 to 3 for ticket 09, after 06 deploys the App |
| 11, the first 20 documents | P1 | 0fbdb58 | e0721da | Round 2 passed all 8 criteria offline and parked the live halves of criteria 3 and 7, in `.notes/11-verify-r2.md` | Not yet. Catch-up steps 1 to 4 for ticket 11 |

Tickets 04, 07, 08, 09 and 11 count as done for the frontier. Their parked criteria and checks stay unproven until the catch-up runs and the verifier re-checks them. Ticket 03 is not done. Its file says `ready-for-human`, set in commit 79a3ab3, and its criteria 2 to 5 are parked.

From dispatch to merge, not counting the user's pause from 10:00 to 12:30 that `.notes/pause-state.md` records, the 11 tickets that landed took 1 hour 46 minutes for 01, 3 hours 32 minutes for 03, 2 hours 30 minutes for 05, 2 hours 23 minutes for 04, 1 hour 29 minutes for 50, 1 hour 45 minutes for 08, 3 hours 59 minutes for 07, 1 hour 9 minutes for 51, 8 hours 36 minutes for 02, 1 hour 20 minutes for 09 and 1 hour 41 minutes for 11. That is a mean of 2 hours 45 minutes and a median of 1 hour 46 minutes. The dispatch and merge commits are in `git log build/strata`.

The gate on `build/strata` passed in 57.5 seconds by hand after ticket 07's merge, at a load average of 35.6, with 53.9 seconds of Python tests in one process. Ticket 51 put those tests on four workers. After its merge the gate passed in 28.6 seconds, then in 28.7 seconds after 02, 29.7 seconds after 09, and 30.3 and 47.6 seconds after 11. Each time comes from that ticket's merger comment.

The catch-up file, `docs/workspace-catchup.md`, holds 21 blocks. The first runs the wizard, the day-one probes and the pay-as-you-go check. Then come ticket 03's steps 1 to 4, ticket 04's steps 1 to 4, ticket 08's steps 1 and 2, ticket 07's steps 1 to 3, ticket 09's steps 1 to 3 and ticket 11's steps 1 to 4.

## Blocked

- Ticket 10 is blocked by 06. Its other blocker, 09, is done.
- Ticket 16 is blocked by 06. Its other blockers, 07 and 11, are done.
- Ticket 12 is blocked by 10, ticket 14 by 10 and 13, and ticket 15 by 12 and 14.
- Ticket 18 is blocked by 16 and 17, and ticket 19 by 17.
- The other 30 open tickets, 20 to 49, wait on tickets that are themselves blocked. Each ticket's `Blocked by` line names its blockers.
- On the user: P0's exit criterion, ticket 03's criteria 2 to 5, ticket 04's criteria 1, 2, 3, 4 and 7, ticket 07's criterion 8, ticket 08's three live checks, the live halves of ticket 09's criterion 6 and ticket 11's criteria 3 and 7, and every live step that later tickets park. All of them wait for the environment file.

## Dates

Today is Friday, October 23, 2026, which is day 1 of about 15, counting October 22 as day 0.

- **October 31, 2026, 8 days left.** P156634, the project behind the demo plan, closes, as `docs/PLAN.md` sections 3 and 16 say. `data/fixture/README.md`, under "Before demo day", gives the recheck steps for two plan rows that the awards dataset contradicts.
  - KE-NWWDA-541055-CW-RFB. The October 9 plan shows no signed contract. The awards dataset shows contract 1903781, signed on June 22, 2026 for US$1,287,515.60, and award notice OP00474946 was published on October 13, 2026. Ticket 09's check_plan marks it Needs a look as of October 22, 2026.
  - KE-NWWDA-541062-CW-RFQ. The plan says Pending Implementation. The awards dataset shows contract 1903551, signed on May 11, 2026. Ticket 09's check_plan marks it Watch, 9 days before closing, as of October 22, 2026.
  - On demo day, run `uv run python -m strata.fixture.record`. It prints a diff and writes nothing until you run it again with `--write`. Then run the gate, which checks every value in `tests/ground_truth/values.toml` against the recorded files.
  - Recheck both rows' signals. If one of the four comparables still open was signed or canceled, move it in `values.toml` and update the counts. If fewer than three stay open, record another Kenya works package under Request for Bids that was still open on the plan's date.
  - Then settle decision 7, the story the demo leads with. P130164 stays the closed showcase.
- **About November 6, 2026, 14 days left.** Round 2 of the interview, where the panel asks for live code changes, as `docs/PLAN.md` section 1 says. The repo says only "about 15 days from October 22", so the real date may differ. See decision 4.
- **November 10, 2026, 18 days left.** The Azure free credit ends, so the subscription moves to pay-as-you-go before then, as `docs/PLAN.md` section 2 says. At 16:06, `dayone.py show` printed "payg: Not done yet". The wizard refuses any pay-as-you-go date on or after November 10. See decision 2.

The schedule check runs on the tickets' `Blocked by` lines and counts build rounds. One build round is the time one ticket takes from dispatch to merge, and the current round, with 06, 13 and 17 in flight, is round 1. With four tickets at once and the longest chain first, the 40 open tickets need 11 rounds, and P1's last ticket, 15, merges in round 4. With three at once they need 14 rounds. At the mean of 2 hours 45 minutes, 11 rounds come to about 30 hours of build time. At the median of 1 hour 46 minutes they come to about 19 hours. At 09:25 the check needed 13 rounds, so two rounds passed in about 4 hours 15 minutes of build time, not counting the pause. Ticket 02 took 8 hours 36 minutes, P2's tickets are larger, and the build stops whenever a session ends, so the real pace is slower. `docs/PLAN.md` section 13 gives no day count for each phase. No phase is over the time the round count gives it, so nothing moves to "designed, not built" yet.

## Risks

**From `docs/PLAN.md` section 16**

- **Free Edition cannot reach the World Bank hosts.** This is day-one test 1, and it says "not run". The live runs of tickets 07, 08, 11 and 17 all fetch from these hosts. The owner is ticket 03, run by the user. Next step: `bash ops/dayone/run-probes.sh --env-file .env` runs the test 1 probe from a notebook, a job and the app. If it fails, ingestion moves to a Container Apps job that pushes files into the volume.
- **The daily quota stops compute during a review.** Nothing runs on the workspace yet. Ticket 08 parses each page once, and ticket 17 makes the nightly job's fetch and bronze-to-gold tasks do real work for every country, which raises the load. Ticket 04 set the nightly job to 05:00 New York time in `bundle/nightly.yml`. The owner is the orchestrator after the wizard, then ticket 43. Next step: catch-up step 4 for ticket 04 records both nightly schedules in `bundle/README.md`, and its Overlap line must start with "- Overlap: none".
- **The app stops 24 hours after each deploy.** The owner is ticket 48. Ticket 06's branch has the deploy command, `ops/app/deploy_app.py`, proven against a fake workspace in `.notes/06-verify-r2.md`. Next step: ticket 06's first live deploy is where the stop first shows up. Ticket 48's demo-ready command restarts and warms the app, in P4.
- **The free credit ends on November 10.** 18 days are left, and pay-as-you-go is "Not done yet". The owner is the user. Next step: decision 2.
- **Prompt Shields refuses real report text.** Ticket 11 stores a shield result for all 733 passages on the fixture, but through the offline stand-in. Ticket 13 now builds the agent that sends real passages through Foundry. The owners are tickets 11 and 13. Next step: catch-up step 4 for ticket 11 counts the live Prompt Shields results, and ticket 13's live check sends passages with rule-like sentences. Both need Foundry, so they wait for the wizard.
- **Supplier names are matched wrongly.** Gold joins a joint venture's members on their supplier IDs, with each amount counted once, as `.notes/07-verify-r6.md` shows for contract 1624689. Ticket 17's round 4 review found a rule that kept a person's name when initials looked like a firm's legal form. The owner is ticket 17 now, then ticket 19, which waits on 17. Next step: review and verify b414976, then ticket 19 matches on IDs first and sends uncertain matches to a person, which needs the labeling time in decision 5.
- **The demo plan's project closes October 31.** That is 8 days away. The owner is the user on demo day, with ticket 05's fixture. Next step: the recheck steps under October 31 in "Dates".
- **"Build complete" outruns the time.** 40 tickets are open, the schedule check needs 11 rounds, and 14 days are left to the assumed Round 2 date. The owner is the PM with the orchestrator. Next step: measure the pace again at the P1 phase gate. If a phase runs over, tickets 43 and 44 move to "designed, not built" first, because Operationalization carries 15 points, the lowest weight in `docs/PLAN.md` section 17. That cuts the longest chain from 11 tickets to 10. With four at once it still needs 11 rounds, so it saves a round only with three or five at once. See decision 6.

**New since planning**

- **Ticket 06 now sits on the longest chain.** 36 tickets wait on it, and it failed one criterion in round 2. Until it merges, only three tickets can run. The owner is the orchestrator. Next step: verify the fix in 3d4e208 with the test the verifier asked for, a 502 `{"code": "unreadable"}` and one usage row, then merge and start tickets 10 and 16.
- **Ticket 17 will conflict when it merges.** Its merge base is c1945f2, and a trial merge at 16:08 conflicts in `src/strata/config.py`, which ticket 11 also changed. The owner is ticket 17's side run, then the merger. Next step: merge `build/strata` into the branch before its last verification, so the verifier checks the merged code.
- **Structured data may not fit in 0.5 GB.** `docs/PLAN.md` section 3 and the spec set the limit. Ticket 17's branch projects 1.57 GB at full scale, with notices alone at 964 MB, as `.notes/17-verify-r2.md` records. The verifier's own estimate puts the notices near 0.5 GB by themselves. The owner is the user for the limit, then ticket 17. Next step: decision 18. Until then the build keeps everything and the workspace measures the real size.
- **Live steps keep piling up while the environment file is missing.** The catch-up file holds 21 blocks, and ticket 06 will add more. A live run may show failures that the offline versions hid. The owner is the user for the wizard, then the orchestrator for the catch-up. Next step: decision 1, then run the blocks in order and have the verifier re-check each parked item.
- **The live notices may keep phone numbers.** CLAUDE.md rule 8 says notice contact details are stripped at ingestion. Ticket 07's merger lists review polish P1: Kenyan numbers after Ph, M, Contact or WhatsApp stay, and so does a second number after "or". No recorded notice uses them, so the offline scan passes, but the live run reads every Kenya notice, and ticket 17's run reads every country's. The owner is the orchestrator. Next step: land the tested fix in `.notes/07-review-r6.md` before catch-up step 1 for ticket 07 runs.
- **Retrieval quality is not measured yet.** Ticket 11 searches with a hashed-words stand-in, not text-embedding-3-large vectors, because no key exists. Analytical and AI methodology carries 30 points. The owner is the orchestrator after the wizard. Next step: record real vectors for the 733 passages in catch-up step 1 for ticket 11, as decision 16 says.
- **Only one layout parser is built.** `config/models.toml` names `ai_parse_document`, and ticket 08's tests use output written by hand in its version 2.0 shape. Day-one test 3 has not run. If it fails, a Content Understanding adapter must join `PARSERS` in `src/strata/reader/layout.py`. The owner is the orchestrator after the user's probes. Next step: catch-up step 1 for ticket 08 proves the real shape.
- **Choices that depart from the rules or the plan wait on the user.** Each has a reason in a merger comment or a note, so none is silent drift. Gold deletes rows with `MERGE ... WHEN NOT MATCHED BY SOURCE THEN DELETE`, while CLAUDE.md rule 5 asks for a `DELETE` with a `WHERE`. Num works out "about N in 10" in the browser, while CLAUDE.md rule 1 makes a derived figure a tool column. `docs/PLAN.md` section 3 says plans are in local currency, but P156634's plan is in US$. The slice is 109 projects by ticket 17's sector rule, not the 128 in section 3. Ticket 09's criterion 2 and ticket 10 say 8 activities, and the plan has 9. The owner is the user, then the orchestrator for the edits. Next step: decisions 13 to 18.
- **The secret scan does not read the incoming branch during a merge.** Ticket 01's verification found this as V1. The mergers for 07, 51, 02, 09 and 11 each scanned the branch's commits by hand first, as their merger comments say. The owner is the merger, through its step 3 in `.claude/agents/merger.md`. Next step: keep the hand scan on every merge. The PM proposes a ticket to have the gate scan the incoming branch itself.
- **Review polish has no ticket to land in.** The merger comments list open polish for tickets 01, 03, 04, 05, 50 and 08. This wave adds P1 to P3, O1, O4 and O5 for ticket 07, P1 to P6 for 51, P1 to P3 and the string lint's gaps for 02, R2-P1 to R2-P6 and V1 to V3 for 09, and P1 to P6 for 11. Three matter before a live run or the change drill: 07's phone labels above, 09's R2-P2, where a data note missing from `config/tools.toml` gives HTTP 500 at run time, and 11's P1 for ticket 16. The owner is the orchestrator with the PM. Next step: the PM proposes one polish ticket, with no ticket waiting on it, and asks that 07's P1 land before the first live run.
- **fairshare cannot be read.** Ticket 02's merger says its ported components were written from `docs/PLAN.md` section 12, DESIGN.md and the briefs. Tickets 06, 13, 33 and 35 also name fairshare code to copy or adapt, and ticket 43 needs fairshare's nightly schedule. The owner is the user for access, and the orchestrator until then. Next step: decision 3.
- **One set of SQL runs on two engines.** Each data ticket checks its ground-truth SQL on DuckDB in the gate. The warehouse side is parked as a same-rows step for tickets 04, 07, 08, 09 and 11. The owner is the orchestrator. Next step: run those steps after the wizard.

**Closed since the last status**

- Ticket 07's failed criterion 3 is fixed. Round 6 passed it, and `docs/PLAN.md` section 3 now names the fifth loan-number form, `6030-KE`.
- Ticket 02's flaky font helper is gone. Round 12's review found no blocking finding, and the verifier ran the gate twice in 33.5 and 31.9 seconds.
- The python lane has four workers. Ticket 51's merge brought the gate from 57.5 seconds to 28.6 seconds by hand.

## Decisions for the user

Each decision says what the build does until you answer. Numbers 1 to 12 keep the numbers they had, because ticket comments cite them.

**First thing in the morning**

1. **Run the wizard and the probes.** This is a step rather than a choice, but P0 cannot close without it. From the main checkout, run `bash ops/wizard/strata-setup.sh`, then `bash ops/dayone/run-probes.sh --env-file .env`, then `bash ops/wizard/strata-setup.sh` once more to finish test 6. Afterwards `grep -c 'None yet. The command above fills it.' docs/day-one-results.md` must print 0. Then the orchestrator runs the other 20 blocks in `docs/workspace-catchup.md` in order. Until then, every live step waits there.
2. **Pay-as-you-go before November 10.** The wizard's pay-as-you-go stage accepts only a date before November 10. Until you do it, `docs/day-one-results.md` says "Not done yet" for pay-as-you-go, and the build keeps spending the free credit.
3. **fairshare access.** Either grant access so the build can compare its code with fairshare's, or accept the rewrite from `docs/PLAN.md` section 12. Ticket 02's merger asks the same question. Until you answer, the build writes the code from the description.
4. **The exact date of Round 2.** The repo says only "about 15 days from October 22". Until you answer, the PM counts to November 6.

**Within about a week**

5. **Labeling time.** Ticket 19 needs about 1,000 supplier pairs labeled, ticket 32 about 150 notice queries judged by two people, and ticket 34 the risks that completion reports blamed, coded by two people. Decide how much you will label, who the second person is, or whether model-drafted labels that you spot-check are acceptable if the proposal says so. Until you answer, the tickets build the labeling tools and report whatever has been labeled.
6. **What gives way first if time runs short.** Nothing needs to give way now. If it does, the PM proposes the lowest rubric weight first. Tickets 43 and 44, Operationalization at 15 points, move to "designed, not built", and ticket 45 shrinks to the one dashboard page that ticket 16 builds. That cuts the longest chain from 11 tickets to 10, which saves a round with three or five tickets at once but not with four. Domain alignment comes next, mainly tickets 35 to 42. Until you answer, nothing is cut.
7. **The demo story for KE-NWWDA-541055-CW-RFB.** The October 9 plan shows no signed contract, while the awards dataset shows one signed on June 22, 2026. Decide whether the demo leads with "no signed contract" or shows the plan and the award row disagreeing. Until you answer, `tests/ground_truth/values.toml` keeps the plan's own values and records the award rows beside them.
8. **Ticket 08's four choices.** They are in ticket 08's merger comment and in `.notes/08-verify-r2.md`. A delay whose first listing could not be confirmed is kept and marked with `first_listing_confirmed` false. The October 9 plan lists nine activities, one more than the wireframe's eight. Words that wrap in a description stay split as the PDF gives them. A delay row takes the later of its two plans' public dates. Until you answer, the build follows these picks.

**From the design briefs**

9. **The briefs' parked choices.** `.notes/parked-decisions.md` lists every choice the design briefs settled so building could go on, in a P1 batch for tickets 06, 10, 12, 14, 15 and 16, then P2 and P3 batches. Until you answer, the build follows each brief. The ones you will see first are on the app shell, which ticket 06 is building now, and on Check a plan.
   - The navy bar marks the selected tab with a white underline and shows keyboard focus in orange, because DESIGN.md's primary and focus colors are too faint on navy. Ticket 02 wrote this into DESIGN.md.
   - The tabs fold into a Menu button below 1024 px, not below 768 px.
   - Check a plan adds two routes for a plan version that `docs/PLAN.md` section 8 does not list.
   - STEP amounts to the cent are settled and need nothing from you. DESIGN.md's Numbers row now says a table keeps STEP's form, 1,230,000.00.

**From this wave's merges**

13. **Ticket 02's choices.** Num works out "about N in 10" and percentages in the browser, as ticket 02's criterion 5 asks, while CLAUDE.md rule 1 says a derived figure is a tool column. Decide whether Num should show only a frequency the tool sends. Also confirm that the shared Button's flush ghost style may lose its side borders, as DESIGN.md section 5 now records. Until you answer, both stay as built.
14. **Ticket 07's choices.** Gold removes rows with `MERGE ... WHEN NOT MATCHED BY SOURCE THEN DELETE`, while CLAUDE.md rule 5 says rows leave only through a `DELETE` with a `WHERE`. The builder kept the MERGE, and `sync()` stops rather than empty a table. Every number after a phone label is removed, firms' office numbers included. An award counts as public from its signing date. Until you answer, all three stay as built. The rest are in ticket 07's merger comment.
15. **Ticket 09's choices.** Its merger comment lists nine picks. Three need you most. First, the plan has 9 activities, so ticket 09's criterion 2 and ticket 10's text should say 9 activities and 3 with no mark, not 8 and 2. Second, a new threshold of US$1,000,000 keeps KE-NWWDA-541062-CW-RFQ at Watch, as the wireframe shows. Third, the tool accepts an as-of date after today and then states events that have not happened. The choice is to answer as of today or to refuse with HTTP 422. Until you answer, the build keeps US$1,000,000, the orchestrator leaves the criterion text as it is, and ticket 13's agent never passes a date after today.
16. **Ticket 11's choices.** The twenty documents are P130164's ICR, two ICR Reviews and 13 ISRs, plus P156634's PAD and its three newest ISRs, because the fixture has no Kenya completion reports. Only emails and labelled phone numbers come out of a document's text, and names stay, since CLAUDE.md rule 8 names only notices. Offline search uses a stand-in for the embeddings, and the live catch-up records real vectors. Until you answer, the build follows these picks. The other two are in ticket 11's merger comment.
17. **The currency of a Procurement Plan.** The P0 phase gate found that `docs/PLAN.md` section 3 says plans are in local currency, but P156634's plan shows US$. Decide whether that sentence changes or the plan reader records each plan's currency. Until you answer, nothing changes, and ticket 17 or 43 can carry the code.

**From ticket 17, still in flight**

18. **The 0.5 GB limit and the slice's size.** Ticket 17's branch projects 1.57 GB of structured data at full scale, three times the 0.5 GB that `docs/PLAN.md` section 3 and the spec set. Its sector rule gives 109 slice projects, not the 128 the plan names. Decide whether the limit rises or less is kept, and which slice count stands. Its reviewer also parked two smaller choices: a governance score counts as public from the day the API last updated it, and a notice or project that a source withdraws after Strata fetched it still counts as held. Until you answer, the build keeps everything, uses 109 projects, and lets the workspace measure the real size.

**Whenever you get to them**

10. **The GitHub repo.** Decide which account owns it when it is first pushed. Creating the repo and adding reviewers is your step. Until you answer, nothing is pushed, under CLAUDE.md rule 10.
11. **Git identity.** Commits in this repo are authored as "Chirag Lakhanpal <chirag.lakhanpal.cl@gmail.com>", set in this repo's git config. Say if you want a different name or email. A change affects only new commits. Until you answer, nothing changes.
12. **The "About this demo" page.** Decide whether the footer gets a page that lists the proposal, the dashboard, the repo and the deck with its speaker notes. Brief 06 left the footer with only the DESIGN.md section 8 sentence. Until you answer, the page stays unbuilt, as the spec says, and the deck stays at `/present` with no link.

**Housekeeping**

19. **A leftover dev server.** A Vite dev server that a design-lead agent started at 03:44 is still running as process 94952 on port 5173, from the removed worktree `.claude/worktrees/wf_3754dbdb-163-2`. It cannot affect the gate or the tests. To clean up, stop that process and delete the folder. The orchestrator left both to you under CLAUDE.md rule 5, as `.notes/orchestrator-parked.md` says. Until you do, it keeps running.
