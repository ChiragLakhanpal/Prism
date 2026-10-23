# Strata build status

_Kept current by the `pm` agent. Last updated October 22, 2026, before the build started._

## Today

Planning is complete: the spec and 49 tickets are in `.scratch/strata/`, the agent team is in `.claude/agents/`, and the guard hook is tested. Next: the user starts a session in this folder and types "make this" or `/build`.

## Phase

P0 Foundations (`docs/PLAN.md` section 13). Exit criterion: every day-one test has a result and a chosen path.

## Frontier

- **01** Repo scaffold and the offline gate.
- **03** Credentials, Azure caps and the day-one tests. Its wizard comes first; the user runs it at the start of the build.

02 (design-system foundation) and 05 (demo and showcase fixtures) follow 01. Everything from 04 onward waits on 03's credentials.

## In flight

None.

## Done

Planning: `docs/PLAN.md`, `GLOSSARY.md`, `DESIGN.md`, ADRs 0001 to 0004, the blueprint, the spec and tickets, the agent team, the guard hook and the build playbook.

## Blocked

None.

## Dates

- **October 31, 2026:** P156634, the demo plan's project, closes. Recheck its signals on demo day.
- **November 10, 2026:** the Azure free credit ends. Move the subscription to pay-as-you-go before then.
- **Round 2:** about 15 days from October 22.

## Risks

See `docs/PLAN.md` section 16. Also: the critical path is 16 tickets deep, so the PM watches the P2 share closely and moves the lowest-weighted work to "designed, not built" first.

## Decisions for the user

- **Labeling time.** Some measures need people: about 1,000 supplier pairs (entity resolution, ticket 19), about 150 judged queries (retrieval, ticket 32) and the hindsight coding (ticket 34). The tickets build the tools and report whatever has been labeled. Decide how much you will label, or whether model-drafted labels that you spot-check are acceptable, if the proposal says so.
- **The GitHub repo.** Which account owns it when it is first pushed: fairshare lives under ChiragLakhanpal. Creating it and adding reviewers is your step, kept out of the credentials wizard.
- **"About this demo".** Whether the footer gets a page listing the proposal, the dashboard, the repo and the deck with its speaker notes. The deck itself stays at `/present` with no button.
- **For awareness.** The tickets run one set of plain SQL on both Databricks and the local DuckDB fixture, through a transpile step (spec, "Data and the lakehouse run"). Revisit this if Lakeflow features get in the way.
