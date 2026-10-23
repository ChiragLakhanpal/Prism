# Strata build status

_Kept current by the `pm` agent. Last updated at 00:12 on Friday, October 23, 2026, from commit 4401ad5 on `build/strata`._

## Today

Tickets 01 and 03 are running again, this time from a session started inside `strata/`, so the guard hook and the named agents are loaded. Commit 4401ad5 set both tickets to `in-progress` at 00:04 on October 23, and their two worktrees were created at 00:07. At 00:09 neither worktree had a commit or a changed file, and `.notes/` was empty, so no review or verifier result exists yet and no ticket is done. The file `.env` is still missing and all 15 keys are unset (checked with `python3 .claude/hooks/guard.py --env-keys` at 00:08). Every step that needs Databricks, Foundry or Azure therefore waits for ticket 03's wizard, and phase P0 cannot close until the user runs it. fairshare still cannot be read: listing its folder failed with "Operation not permitted" at 00:09, so ticket 01 writes the server and web shell from `docs/PLAN.md` section 12. Two things are new since the last status. First, `core.hooksPath` in `.git/config` is now the absolute path of the main checkout's `.githooks` folder, not the relative `.githooks` that the last status recorded. Second, a schedule check on the tickets' `Blocked by` lines shows that the pick order in `docs/agents/issue-tracker.md`, lowest number first, needs 17 days with four tickets at once. Starting the ticket with the longest chain of tickets waiting on it needs 15. The PM's read is that the build can still finish by November 6, the rough Round 2 date, but only with that pick order, four tickets running at all times, and no ticket taking more than a day. The pace is not measured yet, because nothing has merged.

## Phase

P0 Foundations (`docs/PLAN.md` section 13). Its tickets are 01 to 05. Across the whole plan, the tickets' Phase lines count five tickets in P0, 11 in P1, 29 in P2, two in P3 and two in P4, which makes 49.

Exit criterion:

- [ ] Every day-one test has a result and a chosen path. Not met. None of the ten tests in `docs/PLAN.md` section 14 has a result, and the day-one results document from ticket 03 does not exist yet. Ticket 03's second acceptance criterion says the user fills it by running the wizard, because only a person can sign in to the dashboards.

The phase's work, as `docs/PLAN.md` section 13 lists it:

- [ ] The repo with its rules, hooks and gate. Ticket 01 builds it and is in progress. The rules in `CLAUDE.md` and the guard are in place from commit 7d19e07, and the guard's own tests passed at 00:11 on October 23 (8 tests and 134 subtests). The gate itself is missing, because `.githooks/` does not exist on `build/strata` yet.
- [ ] The `strata` catalog. Ticket 04 builds it and waits on 01 and 03.
- [ ] The day-one tests, the model deployments, the Azure caps and pay-as-you-go before November 10. Ticket 03 writes the wizard and the probes and is in progress. The live parts wait for the user.
- [ ] Two more P0 tickets, the design-system foundation (02) and the demo and showcase fixtures (05), each wait on 01.

Looking ahead, P1 ends when the deployed app checks one plan and answers one question with citations, and the offline gate runs in under two minutes (`docs/PLAN.md` section 13). The deployed app needs the live workspace and Foundry, so offline work alone cannot meet P1's exit either.

## Frontier

The frontier is every ticket whose status is `ready-for-agent` and whose blockers are all done (`docs/agents/issue-tracker.md`).

- The frontier is empty right now. Tickets 01 and 03 are the only two with no blockers, and both are in progress.
- When 01 merges, tickets 02 and 05 join the frontier, because 01 is their only blocker.
- Ticket 04 joins when 01 is done and 03 is `ready-for-human`. The standing rules in `docs/agents/build.md` count 03 as satisfied for the frontier once its wizard and probes merge.

## In flight

| Ticket | In progress since | Where | Work at 00:09 |
|---|---|---|---|
| 01, the repo scaffold and offline gate | 00:04 on October 23, commit 4401ad5 | One of the two worktrees below | No commit and no changed file |
| 03, credentials, Azure caps and the day-one tests | 00:04 on October 23, commit 4401ad5 | The other worktree | No commit and no changed file. The wizard has not been reported yet. |

The two worktrees are `.claude/worktrees/wf_d3be378b-34f-2` and `.claude/worktrees/wf_d3be378b-34f-3`, on the branches `worktree-wf_d3be378b-34f-2` and `worktree-wf_d3be378b-34f-3`. Both were created at 00:07 and both sit at 4401ad5. Nothing in the repo records which worktree holds which ticket. Two more branches, `strata/01-repo-scaffold-and-offline-gate` and `strata/03-credentials-caps-and-day-one-tests`, also point at 4401ad5 and hold no work of their own.

## Done (this phase)

No ticket is done. A ticket counts as done only when its file says `done`, it is merged into `build/strata`, and its verifier result passed. Today 47 ticket files say `ready-for-agent` and two, 01 and 03, say `in-progress`. The notes folder `.notes/` is empty, so no verifier result exists.

Groundwork outside the tickets, by commit:

- 7d19e07 "Plan Strata" is `main`'s first commit and holds the planning documents, `CLAUDE.md` and the guard.
- 450095b adds `docs/workspace-catchup.md`, the list of live steps to run once `.env` is filled.
- c48b532 adds the standing rules in `docs/agents/build.md` and pins every agent to Opus 5.5 at effort `xhigh`.
- 4401ad5 adds `docs/agents/unslop.md`, the writing rules the user asked for. It is a rule file for agents, not product work, so it needs no ticket.

Parked live checks: none yet. `docs/workspace-catchup.md` holds only its introduction. When a ticket merges with live checks still to run, the PM lists them here beside the ticket, so no ticket is described as proven live when it is not.

## Blocked

- Tickets 02 and 05 are blocked by 01.
- Ticket 04 is blocked by 01 and 03.
- Ticket 06 is blocked by 02, 03 and 04.
- Tickets 07 and 08 are each blocked by 04 and 05.
- Ticket 09 is blocked by 07 and 08.
- The other 40 tickets, 10 to 49, are blocked by tickets that are themselves blocked. Each ticket's `Blocked by` line names its own blockers. Ticket 01 sits under 47 tickets and ticket 03 under 45. The longest chain is 15 tickets: 01, 04, 07, 09, 11, 13, 14, 15, 30, 34, 44, 45, 46, 47 and 49.
- On the user: phase P0's exit criterion, and every live check that later tickets park in `docs/workspace-catchup.md`, wait for the wizard to fill `.env`.

## Dates

Today is Friday, October 23, 2026, which is day 1 of about 15, counting October 22 as day 0.

- **October 31, 2026, 8 days left.** P156634, the project behind the demo plan, closes (`docs/PLAN.md` sections 3 and 16).
- **About November 6, 2026, 14 days left.** Round 2 of the interview, where the panel asks for live code changes. The repo says only "about 15 days from October 22", so the real date may differ.
- **November 10, 2026, 18 days left.** The Azure free credit ends, so the subscription moves to pay-as-you-go before then (`docs/PLAN.md` section 2). That step is in ticket 03's wizard.

The schedule check behind these dates assumes four tickets at once and one day per ticket from start to merge. Picking the ticket with the longest chain first, P0's offline work ends on day 2 (October 24), P1's on day 8 (October 30) and the whole plan on day 15 (November 6). Picking the lowest number first, the plan ends on day 17 (November 8). With three tickets at once, either order ends on day 17.

## Risks

**From `docs/PLAN.md` section 16**

- **Free Edition cannot reach the World Bank hosts.** This is day-one test 1, and it has no result because there are no credentials. Owner: ticket 03. Next step: after the wizard, the test 1 probe runs from a notebook, a job and the app. If it fails, ingestion moves to a Container Apps job that pushes files into the volume.
- **The daily quota stops compute during a review.** Nothing runs on the workspace yet. Owner: ticket 04, then ticket 43. Next step: ticket 04 places Strata's nightly job at an hour that does not overlap fairshare's, and its acceptance criteria ask for fairshare's schedule. The build cannot read that schedule until fairshare is readable or the user supplies it.
- **The app stops 24 hours after each deploy.** Owner: ticket 48. Next step: ticket 06 deploys the first app, which is where the stop first shows up. Ticket 48's demo-ready command restarts and warms it, in P4.
- **The free credit ends on November 10.** 18 days are left. Owner: the user. Next step: run the wizard's pay-as-you-go stage. If it is not done when ticket 03 closes, its results document records a dated step and who takes it.
- **Prompt Shields refuses real report text.** Owner: tickets 11 and 13. Next step: ticket 11 stores a Prompt Shields result for every passage, and ticket 13 sends real passages that contain rule-like sentences through the live agent. Both live checks need Foundry, so they wait for the wizard.
- **Supplier names are matched wrongly.** Owner: ticket 19. Next step: nothing starts before ticket 17 merges. IDs decide first, there are no supplier scores, and a person decides the uncertain matches, which needs the labeling time in decision 5 below.
- **The demo plan's project closes October 31.** That is 8 days away and about a week before Round 2. Owner: ticket 05 for the fixture, the user for demo day. Next step: ticket 05 records the plan versions up to October 9, 2026, and its recording command refetches every source and prints a diff. Run it on demo day and note whether P156634 closed or got a new closing date. P130164 stays the closed showcase.
- **"Build complete" outruns the time.** The plan has 49 tickets and 14 days left. The schedule check above shows exactly 15 days of work with four tickets at once, the longest chain first, and one day per ticket, so there is no spare day. The restart cost about 50 minutes: the first dispatch was in commit 450095b at 23:17 on October 22 and the second in 4401ad5 at 00:04 on October 23. Owner: the PM with the orchestrator. Next step: measure the pace when 01 merges and again at the P1 gate. If a phase runs over its share, the first cut is tickets 43 and 44, Operationalization at 15 points, the lowest rubric weight in `docs/PLAN.md` section 17. Moving both to "designed, not built" brings the schedule to 14 days. See decision 6.

**New since planning**

- **The hooks path now points at the main checkout.** `.git/config` sets `core.hooksPath` to the absolute path of the main checkout's `.githooks`. The status from commit c48b532 recorded the relative path `.githooks`, chosen so each worktree runs its own copy of the gate. Nothing in the repo records the change. All worktrees share this setting. Until ticket 01 merges, no commit anywhere runs a gate, because that folder does not exist in the main checkout. That includes ticket 01's own commits, so its second acceptance criterion, that a commit with a failing test is blocked, cannot be shown in its worktree as things stand. After 01 merges, every worktree commit runs the main checkout's copy of the hook, so a ticket that changes the gate is checked by the old gate. Owner: the orchestrator. Next step: run `git config core.hooksPath .githooks` in the main checkout before ticket 01's first commit, or record why the absolute path is wanted. Either way, ticket 01's reviewer checks that the hook finds the repo root with `git rev-parse --show-toplevel`, so it tests the worktree's files and not the main checkout's.
- **The pick order costs two days.** `docs/agents/issue-tracker.md` says to start the lowest-numbered ready ticket first when more are ready than can run. With four at once, that order needs 17 days and ends on November 8. Starting the ticket with the longest chain of tickets waiting on it needs 15. Owner: the orchestrator. Next step: pick by longest chain from the first wave after 01 merges, and record the reason in `docs/agents/build.md`, so the change is not unrecorded drift from the tracker's rule.
- **Credentials are missing, so live steps are parked.** All 15 keys in `.env.example` are unset (checked at 00:08 on October 23). Tickets will merge with their workspace steps still to run. A live run may then show failures that the offline versions hid. A failed day-one test could also change a path that tickets were built on, for example by moving ingestion to a Container Apps job. Owner: the user for the wizard, then the orchestrator for the catch-up. Next step: run the wizard first thing, run the blocks in `docs/workspace-catchup.md` in order, and have the verifier re-check each parked criterion.
- **fairshare cannot be read.** Listing the folder, and its parent, failed with "Operation not permitted" at 00:09 on October 23. Tickets 01, 02, 06, 13, 33 and 35 name fairshare code to copy or adapt, and tickets 04 and 43 need its nightly schedule. The code is written from section 12's description, which lists eight known traps to design around. Owner: the user for access, the orchestrator until then. Next step: decision 2 below. If access comes, the PM proposes a ticket to compare the rewritten files with fairshare's.
- **Ticket 01 sits under 47 tickets.** It has nine acceptance criteria, and its shell is written without fairshare to copy from. Owner: the orchestrator. Next step: send 01 to review, verification and merge as soon as it reports, because its merge sets the pace for the rest of the plan.
- **One set of SQL runs on two engines.** The tickets run the same plain SQL on Databricks and on the local DuckDB fixture through one transpile step (spec, "Data and the lakehouse run"). Owner: ticket 04, which adds the transpile step. Next step: revisit the approach if Lakeflow features get in the way.

The first session's missing guard, a risk in the last status, is resolved. This session started inside `strata/` and the guard runs before every tool call.

## Decisions for the user

Each decision says what the build does until you answer.

**First thing in the morning**

1. **Run the wizard from ticket 03.** This is a step rather than a choice, but phase P0 cannot close without it. It walks you through the Databricks token, the Foundry project, the four model deployments and their token limits, the Azure budgets, Application Insights, the sign-in for Foundry evaluations, an outside email invite for the access test, and the move to pay-as-you-go before November 10. Ticket 03's implementer reports the exact command to run from the main checkout. Until then, every live step waits in `docs/workspace-catchup.md`.
2. **fairshare access.** Either grant access so the build can compare its code with fairshare's, or accept the rewrite from the description in `docs/PLAN.md` section 12. The PM leans toward granting access if it takes a minute, because six tickets name fairshare code and the plan lists eight traps that cost fairshare days. Until you answer, the build writes the code from the description.
3. **Git identity.** Commits in this repo are authored as "Chirag Lakhanpal <chirag.lakhanpal.cl@gmail.com>", set only in this repo's `.git/config`. Say if you want a different name or email. A change affects only new commits. Until you answer, nothing changes.
4. **The exact date of Round 2.** The repo says only "about 15 days from October 22". Until you answer, the PM counts to November 6, which leaves no spare day in the schedule.

**Within about a week**

5. **Labeling time.** Some measures need people. Ticket 19 needs about 1,000 supplier pairs labeled, ticket 32 about 150 notice queries judged by two people, and ticket 34 the risks that completion reports blamed, coded by two people. Decide how much you will label, who the second person is, or whether model-drafted labels that you spot-check are acceptable if the proposal says so. Until you answer, the tickets build the labeling tools and report whatever has been labeled.
6. **What gives way first if time runs short.** The PM proposes this order, lowest rubric weight first (`docs/PLAN.md` section 17). First comes Operationalization, 15 points: tickets 43 and 44 move to "designed, not built", and ticket 45 shrinks to the one dashboard page that ticket 16 builds. That saves one day of the 15. Then comes Domain alignment, 25 points, mainly tickets 35 to 42. Last come the Architecture and AI methodology tickets, 30 points each. Cutting 43 or 44 means updating the `Blocked by` line of ticket 45. Tickets 28, 31, 41 and 42 can go with no other change, because no ticket waits on them, but cutting them saves no day with four tickets at once. Until you answer, nothing is cut. The PM brings this back when 01 merges or at the P1 gate if the pace calls for it.

**Whenever you get to them**

7. **The GitHub repo.** Which account owns it when it is first pushed. The repo does not say which account holds fairshare. Creating the repo and adding reviewers is your step. Until you answer, nothing is pushed (`CLAUDE.md` rule 10).
8. **The "About this demo" page.** Whether the footer gets a page listing the proposal, the dashboard, the repo and the deck with its speaker notes. Until you answer, it stays unbuilt, as the spec says. The deck itself stays at `/present` with no button.
