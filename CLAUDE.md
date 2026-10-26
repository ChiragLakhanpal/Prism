# Strata: rules for working in this repo

Procurement intelligence on World Bank open data: every claim cited to a record or a numbered paragraph, every number from a tool. Built for a World Bank interview panel that will also ask for live code changes.

## Start here

- **"make this", "build it", "continue the build"**, or `/build`: you are the orchestrator. Follow `docs/agents/build.md`.
- What to build and why: `docs/PLAN.md` (scope, data, formats, phases), `docs/blueprint/strata-blueprint.html` (screens and the reasoning behind each), `docs/assessment.md` (the brief and its rubric).
- Words: `GLOSSARY.md`. Look, components and copy: `DESIGN.md`. Decisions: `docs/adr/`.
- The work: `.scratch/strata/spec.md` and one ticket per file in `.scratch/strata/issues/`. Progress: `docs/STATUS.md`.

## Rules

1. **Numbers come from tools.** Strata states only numbers a tool returned, at the same rounding; a derived figure is a tool column. The verifier runs on every answer and is never bypassed.
2. **Every claim cites its source**: a query result, or a numbered paragraph with its page. A sentence that can't be checked is removed and shown.
3. **Glossary words, World Bank usage.** Use `GLOSSARY.md` terms and STEP's field names; `DESIGN.md` section 7 lists the words Strata never writes.
4. **One source of truth per definition.** Each measure and each tool contract is defined once; changing one means updating its benchmark question in the same change.
5. **Nothing destructive.** `CREATE OR REPLACE` changes a table; rows leave only through a `DELETE` with a `WHERE`. `.claude/hooks/guard.py` enforces rules 5, 6, 7 and 10 before every tool call; when it blocks you, follow the reason it gives.
6. **The gate runs before every commit** (`.githooks/pre-commit`): the ground-truth SQL and the offline test suite, in under 150 seconds (two minutes until October 26, 2026; back to two minutes after the polish pass trims the tests).
7. **Secrets stay in `.env`** (gitignored, in the main checkout only). `python3 .claude/hooks/guard.py --env-keys` shows which keys are set without their values. Inside the Databricks App, the viewer's forwarded token is bound per request; nothing about a viewer lives in a module global.
8. **Public data in, private uploads kept private.** Notice contact details are stripped at ingestion; a borrower's uploaded plan or PPSD is visible only to the uploader's team.
9. **Changeability.** Each extension point (sources, tools, signals, thresholds, the slice, models, copy, benchmark questions) lives in one registry or config file, so a change request lands in under ten minutes.
10. **Git.** During a build the user started, commit on ticket branches and on the integration branch `build/strata`; the first run also commits the planning documents as `main`'s first commit. After that, pushing, opening PRs and changing `main` wait for the user's go-ahead.

## Agent skills

### Issue tracker

Local markdown under `.scratch/strata/`: the spec, and one file per ticket with its `Status` and `Blocked by` lines. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default role strings, used on each ticket's `Status` line. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
