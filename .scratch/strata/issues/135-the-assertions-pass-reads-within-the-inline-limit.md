# 135: The assertions pass reads the warehouse within the inline limit and can be scoped to a list of projects

**What to build:** On October 29, 2026 at about 20:05 PDT the owner ran the assertions pass by hand (`ops/assertions/batch_live.py` with the environment file) to turn the ISR ratings of the demo projects into assertions, and it stopped at once: "The warehouse did not run the statement. Its state was FAILED: Inline byte limit exceeded. Statements executed with disposition=INLINE can have a result size of at most 26214400 bytes." The pass (`src/strata/knowledge/assertions.py`: `run`, `ProjectRows`, the queries under `src/strata/knowledge/sql/assertions/`) reads one query a family for every project in `default_projects` at once (every project with a document, contract, notice, plan version or IEG rating, about 2,200 today), and at the workspace's size one of those results passes 25 MiB, the statements API's inline cap, which ticket 123 met for plan versions. Make the pass read within the cap in one place and stay scoped: (1) the family queries that grow with the workspace (`records.sql`, `isr_ratings.sql`, `reports.sql`, `report_passages.sql`, whichever the owner's run tripped on) read per project or in pages of a size named in `config/thresholds.toml` [warehouse] (a `statement_result_bytes` cap with the page size derived from it), through one helper on the engine that the plan reader of ticket 123 can share, so no statement of the pass can exceed the cap whatever the workspace holds; (2) `ops/assertions/batch_live.py` takes `--projects P1,P2,...` to run the pass for a list of projects (the nightly keeps its default), printing per project what became assertions and what went to the batch; (3) tests on the fixture with a fake warehouse that refuses any result over a small cap, proving the pass completes in pages, and a test of the `--projects` scope. The live proof is the owner's: the command runs to completion for the five demo projects (P156634, P130164, P161305, P155350, P113151) and the P156634 Timeline tab shows the ISR rating bands, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `ops/assertions/batch_live.py` (`run_live`, `main`), `src/strata/knowledge/assertions.py` (`run`, `ProjectRows`, `_rows`, `default_projects`), `src/strata/lakehouse/engine.py` (`WarehouseEngine.run`, the INLINE disposition, `insert_rows`' chunking), ticket 123's done comment and its code for the plan versions, `config/thresholds.toml` [warehouse].

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] No statement of the assertions pass can exceed the inline cap: the growing family queries read per project or in pages through one engine helper with its cap in `config/thresholds.toml`, proven by a fixture test with a fake warehouse that refuses results over a small cap.
- [ ] `ops/assertions/batch_live.py --projects P1,P2` runs the pass for those projects only and reports per project (a test), while the nightly's default is unchanged.
- [ ] On the paid workspace the owner's command completes for the five demo projects and the P156634 Timeline tab shows the ISR rating bands (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened from the owner's failed run of the assertions pass at about 20:05 PDT.
