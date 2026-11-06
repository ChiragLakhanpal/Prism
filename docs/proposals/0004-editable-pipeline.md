# Proposal 4: An update pipeline that admins can edit

**From:** ProcIntel, `src/procintel/pipeline/rules.py` and `docs/event-pipeline-design.md` (Surya Yadav, October to November 2026)
**Status:** proposed, November 6, 2026

## The idea, as ProcIntel built it

ProcIntel's data updates are events: a notice added or changed, a document added, a supervision document changed, an upload ingested. Rules say which actions run when an event happens, with an optional condition on the fields that changed: "notices-update-packages" runs `apply_notices`, `rebuild_tables` and `rebuild_firms` on a notice event; "documents-ingest" runs the document chain. The default rules ship in the code; rules edited on the Settings page are saved after validation (known event types only, field conditions on watched fields only, actions from the registry only, and no cycle in which an action's derived events lead back to it). `plan()` turns a batch of events into one ordered list of actions, each run once in the registry's order, which follows the data's dependencies. `dry_run()` shows what a rule set would have done on the last seven days' events, and `reset()` restores the defaults.

## How it would work in Prism

Prism's nightly job is a fixed chain in a bundle: fetch each source, bronze, silver, gold, the knowledge tables, the measures. The pipeline makes the chain a set of rules an admin can read, change and try without a deploy.

- **Events.** One per source in `config/sources.toml`, raised by the fetch tasks: `awards.updated`, `notices.updated`, `projects.updated`, `documents.added`, `plans.added`, and the upload's `upload.ingested`.
- **Actions.** The nightly's tasks as the registry names them, in the order the data needs: the silver transform of the source, the gold tables that read it, the passages, the assertions and disagreements, the measures, the warm-up of the page caches.
- **Rules.** `config/pipeline.toml` ships the defaults, one rule per event, so a new source is one rule beside its registry entry (CLAUDE.md rule 9). An admin edits the rules on a page under Data: each rule shows its event, its actions and its last run; validation refuses an unknown event or action and a cycle, with a sentence; "Try it" shows what the rules would have done on the last seven days' events; "Reset" restores the file's defaults.
- **The run.** A batch of events becomes one ordered list of actions, each run once, as one job run with one record in `strata.ops`, so the Data readiness page and the lineage of an answer still trace every table to the run that built it.
- **Guardrails.** Only an admin role edits; the file's defaults never change from the page; a rule that would skip a table another rule reads is refused.

## What changes from ProcIntel

ProcIntel runs the actions in one process on one machine; Prism's actions are job tasks on the workspace, so a rule set becomes a job run with tasks and dependencies, and "Try it" reads the job's history instead of a local event log. ProcIntel keeps 30 days of events; Prism keeps them with the run records in `strata.ops`.

## Open questions

1. Is the admin role a fourth view, or a setting on a staff account?
2. Do rules run on a schedule only, or also when an upload lands?
3. How does a changed rule set reach the bundle: a deploy from the file, or the job reading the table?
