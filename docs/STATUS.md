# Strata build status

_Kept current by the `pm` agent. Last updated late on October 22, 2026, when the first session was stopped so the build could restart inside `strata/`._

## Today

The build started on the night of October 22, 2026, and was reset once. The first session had been started one folder above `strata/`, so the guard hook and the seven named agents never loaded. Two builders had started on tickets 01 and 03 in their own worktrees but had not committed anything, so the orchestrator stopped them, removed the worktrees, set both tickets back to `ready-for-agent`, and pinned every agent to Opus 5.5 at effort `xhigh` in its frontmatter. The next session starts inside `strata/` and continues from here: its first wave is tickets 01 (repo scaffold and offline gate) and 03 (credentials, Azure caps and the day-one tests). The user asked that the build keep going until morning, so every open question is parked in "Decisions for the user" below, and the standing rules for the night are written down in `docs/agents/build.md`. The PM's read is that the build is at risk but not behind: nothing has slipped, but the plan has no spare time (see Risks). The file `.env` is missing, so all 15 keys in `.env.example` are unset. The build therefore uses the offline version of each part that would call the outside world (the DuckDB fixture, the scripted agent and the mocked API) and parks every step that needs Databricks, Foundry or Azure in `docs/workspace-catchup.md`. Ticket 03's wizard will be ready for the user to run in the morning, and phase P0 cannot finish until they do, so its exit criterion is recorded as not met. The sibling repo `fairshare` cannot be read on this machine, so the server and web shell are written from the description in `docs/PLAN.md` section 12 instead of copied.

## Phase

**P0 Foundations** (`docs/PLAN.md` section 13). Tickets 01 to 05 belong to this phase. Across the whole plan, the tickets' Phase lines count 5 tickets in P0, 11 in P1, 29 in P2, 2 in P3 and 2 in P4, which makes 49.

Exit criterion:

- [ ] Every day-one test has a result and a chosen path. **Not met.** None of the ten tests in `docs/PLAN.md` section 14 has a result, and the day-one results document that ticket 03 writes does not exist yet. The user has to run ticket 03's wizard first, because only a person can sign in to the dashboards.

Where the phase's work stands:

- The repo with its rules, hooks and offline gate is ticket 01, which is ready to start.
- The `strata` catalog and bundle skeleton is ticket 04, which waits on 01 and 03.
- The day-one tests, model deployments, Azure caps and the move to pay-as-you-go are ticket 03, which is ready to start. Its live parts wait for the wizard run.
- The design-system foundation (02) and the demo and showcase fixtures (05) are also P0 tickets, and both wait on 01.

Looking ahead, P1 ends when the deployed app checks one plan and answers one question with citations (`docs/PLAN.md` section 13). That needs the live workspace and Foundry, so offline work alone cannot meet it either.

## Frontier

The frontier is the set of tickets that are ready to start: status `ready-for-agent` with every blocker done (`docs/agents/issue-tracker.md`).

- The frontier is tickets 01 and 03, the only two with no blockers. The next session dispatches both in the first wave. Ticket 03 writes its wizard first, so the wizard is ready when the user wakes.
- When 01 merges, tickets 02 and 05 join the frontier. Ticket 04 joins once 03 counts as satisfied. Ticket 03 will be set to `ready-for-human` when its wizard and probes merge, and from then on it counts as satisfied for offline work.

## In flight

None. The first session's two worktrees were removed before either had a commit, and their branches were deleted. The notes folder `.notes/` is empty, so no review or verifier result exists yet.

## Done (this phase)

No ticket is done. A ticket counts as done only when its file says `done`, it is merged into `build/strata`, and its verifier result passed. All 49 ticket files say `ready-for-agent`.

Groundwork finished tonight, outside the tickets:

- The planning documents are committed as `main`'s first commit, 7d19e07 "Plan Strata".
- The branch `build/strata` is checked out in the main checkout, with `core.hooksPath` set to `.githooks` (a relative path, so each worktree runs its own copy of the gate once ticket 01 adds it). Its commits add `docs/workspace-catchup.md`, this status, the standing rules in `docs/agents/build.md`, and the Opus 5.5 pin in every agent's frontmatter.
- The destructive-command guard's own tests pass: 8 tests, run on October 22.
- Tooling is installed: uv 0.13.5, Python 3.12.15 through uv, Databricks CLI v1.22.1 and Azure CLI 2.91.0.

Parked live checks: none yet, because `docs/workspace-catchup.md` holds only its introduction. When a ticket merges with live checks still to run, the PM will list them here beside the ticket, so no ticket is described as proven live when it is not.

## Blocked

- Tickets 02 and 05 are blocked by 01.
- Ticket 04 is blocked by 01 and 03.
- Ticket 06 is blocked by 02, 03 and 04. Tickets 07 and 08 are each blocked by 04 and 05. Ticket 09 is blocked by 07 and 08.
- The other 40 tickets, 10 to 49, are blocked by tickets that are themselves blocked. Each ticket's `Blocked by` line lists its own blockers. The longest chain is 15 tickets: 01, 04, 07, 09, 11, 13, 14, 15, 30, 34, 44, 45, 46, 47, 49. (The earlier status said 16. Counting the tickets in this chain gives 15.)
- On the user: phase P0's exit criterion, and every live check parked in `docs/workspace-catchup.md`, wait for the wizard to fill `.env`.

## Dates

Today is Thursday, October 22, 2026, which is day 0 of about 15.

- **October 31, 2026, 9 days left.** P156634, the project behind the demo plan, closes. Its signals get rechecked on demo day (`docs/PLAN.md` section 16).
- **About November 6, 2026, 15 days left.** Round 2 of the interview, where the panel asks for live code changes, is about 15 days from October 22. The repo gives only this rough figure, so the real date may differ.
- **November 10, 2026, 19 days left.** The Azure free credit ends, so the subscription must move to pay-as-you-go before then. That step is in ticket 03's wizard.

## Risks

**From `docs/PLAN.md` section 16**

- **Free Edition cannot reach the World Bank hosts.** This is day-one test 1, and it is untested because there are no credentials. Owner: ticket 03. Next step: after the wizard, the test 1 probe (a one-command script) runs from a notebook, a job and the app. If it fails, ingestion becomes a Container Apps job that pushes files into the volume.
- **The daily quota stops compute during a review.** Nothing runs on the workspace yet, so this is not in play. Owner: ticket 04, then ticket 43. Next step: ticket 04 puts Strata's nightly job at an hour away from fairshare's. That needs fairshare's schedule and job times, which the build cannot get until the wizard has run or fairshare becomes readable.
- **The app stops 24 hours after each deploy.** Owner: ticket 48. Next step: ticket 06 deploys the first app and is where the stop will first show up. The fix, the demo-ready command, comes in P4.
- **The free credit ends on November 10.** 19 days are left. Owner: the user. Next step: run the wizard's pay-as-you-go stage. If it is not done when ticket 03 closes, that ticket's results document must record a dated step and who takes it.
- **Prompt Shields may refuse real report text.** Owner: tickets 11 and 13. Next step: ticket 11 stores a Prompt Shields result for every passage, and ticket 13 must pass five real passages that contain rule-like sentences through the live agent. Their live checks need Foundry, so they wait for the wizard.
- **Supplier names could be matched wrongly.** Owner: ticket 19. Next step: nothing can start before ticket 17 merges. IDs decide first, no supplier scores exist, and a person decides the uncertain matches, which needs the labeling time in Decisions below.
- **The demo plan's project closes October 31.** That is 9 days away and about a week before Round 2, so by demo day P156634 will have closed or been given a new closing date. Owner: the user for demo day, ticket 05 for the fixture. Next step: ticket 05 records the plan versions up to October 9, 2026 and builds a command that refetches them. Run it on demo day and note which of the two happened. P130164 stays the closed showcase.
- **"Build complete" outruns the time.** The plan has 49 tickets and about 15 days. The longest chain of waiting tickets is 15 deep. A quick schedule check on the `Blocked by` lines shows that with four tickets running at once and each taking one full day from start to merge, the whole plan needs exactly 15 days. A ticket that takes longer uses time that does not exist. Nothing has merged yet, so there is no measured pace. Owner: the PM with the orchestrator, the agent that runs the build. Next step: measure the pace when 01 merges and again at the P1 gate, then use the cut order in Decisions below if it falls short.

**New since planning**

- **Credentials are missing, so live steps are parked.** All 15 keys in `.env.example` are unset (checked with `python3 .claude/hooks/guard.py --env-keys` on October 22). Tickets will merge with their workspace steps still to run. A live run may then show failures that the offline versions hid, and a failed day-one test could change a path that tickets were built on, for example by moving ingestion to a Container Apps job. P1's exit also needs the live workspace. Owner: the user for the wizard, then the orchestrator for the catch-up. Next step: run the wizard first thing, run the blocks in `docs/workspace-catchup.md` in order, and have the verifier re-check each parked criterion.
- **fairshare cannot be read.** Listing the folder, and listing its parent, both fail with "Operation not permitted". Tickets 01, 02, 06, 13, 33 and 35 name fairshare code to copy or adapt, and tickets 04 and 43 need its nightly schedule. Until the user decides, the code is written from `docs/PLAN.md` section 12, which lists eight known traps to design around. Owner: the user for the access decision, the orchestrator until then. Next step: the decision below. If access comes, the PM will propose a ticket to compare the rewritten files with fairshare's.
- **Ticket 01 gates 47 tickets.** It has nine acceptance criteria and a shell written without fairshare to copy from. Owner: the orchestrator. Next step: send 01 to review, verification and merge as soon as it reports, because its merge sets the pace. At review, check one detail. `core.hooksPath` is the relative path `.githooks` in the shared git config, so a commit in a worktree runs that worktree's own copy of the gate. The hook must still find the repo root from the current folder (`git rev-parse --show-toplevel`), or it will test the wrong files.
- **The first session ran without the guard.** It had started one folder above `strata/`, so the guard hook and the named agents never loaded. It was stopped before any ticket commit. Owner: the user. Next step: start every build session with `cd strata && claude`. The standing rules for a session that finds missing credentials or an unreadable fairshare are now in `docs/agents/build.md`, so later sessions and agents follow the same rules.
- **One set of SQL runs on two engines.** The tickets run the same plain SQL on Databricks and on the local DuckDB fixture through one transpile step (spec, "Data and the lakehouse run"). Owner: ticket 04, which lands the transpile step. Next step: revisit the approach if Lakeflow features get in the way.

## Decisions for the user

**First thing in the morning**

1. **Run the wizard from ticket 03.** This is a step rather than a choice, but phase P0 cannot close without it. It walks you through the Databricks token, the Foundry project, the four model deployments and their token limits, the Azure budgets, Application Insights, the sign-in for Foundry evaluations, an outside email invite for the access test, and the move to pay-as-you-go before November 10. Ticket 03's implementer reports the exact command to run from the main checkout.
2. **fairshare access.** Either grant access so the build can compare its code with fairshare's, or accept the rewrite from the description in `docs/PLAN.md` section 12. The PM leans toward granting access if that takes only a minute, because six tickets name fairshare code and the plan lists eight traps that cost fairshare days. If you accept the rewrite, tell the orchestrator so the plan's "copy" wording can be updated.
3. **Git identity.** Commits in this repo are authored as "Chirag Lakhanpal <chirag.lakhanpal.cl@gmail.com>", set only in this repo's `.git/config`. Say if you want a different name or email. A change affects only new commits.
4. **The exact date of Round 2.** The repo says only "about 15 days from October 22". An exact date lets the PM count against the right day.

**Within about a week**

5. **Labeling time.** Some measures need people: about 1,000 supplier pairs (ticket 19), about 150 notice queries judged by two people (ticket 32) and the risks that completion reports blamed, coded by two people (ticket 34). The tickets build the tools and report whatever has been labeled. Decide how much you will label, who the second person is, or whether model-drafted labels that you spot-check are acceptable, if the proposal says so.
6. **What gives way first if time runs short.** The PM proposes this order, lowest rubric weight first (`docs/PLAN.md` section 17). First comes Operationalization and Scalability, 15 points: tickets 43, 44 and 45, where 45 could shrink to the one dashboard page that ticket 16 builds. Then comes Domain alignment, 25 points: mainly tickets 35 to 42. Last come the Architecture and AI methodology tickets, 30 points each. Cutting 43, 44 or 45 means updating the `Blocked by` lines of tickets 45, 46 and 49. Tickets 28, 31, 41 and 42 can be cut with no other change, because no ticket waits on them. You do not need to answer yet. The PM brings this back at the P1 gate if the pace calls for it.

**Whenever you get to them**

7. **The GitHub repo.** Which account owns it when it is first pushed. The planning notes say fairshare lives under ChiragLakhanpal. Creating the repo and adding reviewers is your step. Nothing is pushed until you say so (`CLAUDE.md` rule 10).
8. **The "About this demo" page.** Whether the footer gets a page listing the proposal, the dashboard, the repo and the deck with its speaker notes. The spec leaves it unbuilt unless you add it. The deck itself stays at `/present` with no button.
