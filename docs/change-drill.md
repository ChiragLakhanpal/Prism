# The change drill

In round 2 the panel may ask for a live change to Prism. docs/PLAN.md section 15 lists the ten changes it is most likely to ask for, and each one lives in one registry or config file, so it lands in under ten minutes with the gate green. This runbook gives the steps for each change.

`config/change_drills.toml` is the one list of the ten changes, with the one place each lives and the file of the test that proves it. Each entry below starts with the same place and test, and `tests/test_change_drill.py` fails when they differ. How long each rehearsal took is in `docs/proposal/rehearsals.toml`, and the proposal's Module 4 table shows those times.

## What "one place" means here

The change itself lives in one file. The gate also keeps some files in step with that file, and a drill updates them in the same commit:

- Recorded answers. The screen tests serve recorded API answers from `tests/fixtures/api`, and a test checks that the server still gives each one. When a change alters what a route answers, a command under `tests/` writes the recordings again from the fixture database. Build the fixture first, with `uv run --frozen python gates/build_fixture.py`.
- Tests that state the old value. Some tests type a planning document's value on purpose, such as PLAN.md section 5's order of the evidence ladder, or a screen's words in full. When the panel changes that value, the test changes with it.

No drill edits `tests/ground_truth/values.toml`. That file holds what the World Bank's records say, and a change to Prism never changes a record.

## How to rehearse a drill

1. Make a branch of its own from the branch you are on, named `drill/<nn>-<change>`, such as `git switch -c drill/03-change-a-signal-threshold`. Never merge it. Ticket 49's rehearsal ran on `drill-49/<nn>-<change>` branches, which also count as drill branches.
2. Start the timer, and follow the drill's steps.
3. Commit. Git runs the gate, and the drill ends when the commit is made with the gate green. A red gate means the drill is not done: fix what it reports and commit again.
4. Switch back to the ticket branch, then write the time, the branch, the commit and the gate's seconds in `docs/proposal/rehearsals.toml`. Write the commit's own date, from `git log -1 --format=%aI <commit>`, as its `gate_started_at`. Git dates a commit before the gate runs, so that is when the edits were done, and the proposal's Annex 1 gives the editing time from it.

The gate runs the Python tests in two lanes side by side, python-1 and python-2, and each lane starts with the build of the fixture database (ticket 119). A drill that changes a file the build reads, such as `config/thresholds.toml`, `config/slice.toml`, `config/tools.toml`, the server's copy of the Data readiness sentences, a recorded file or a table definition, makes the build run again, which adds 15 to 30 seconds to both lanes. A drill that changes none of them, such as one that adds a benchmark question, keeps the database, and the build says so in one line. `data/out/fixture.inputs.json` lists every file the last build read. The same holds when a drill's steps run `uv run --frozen python gates/build_fixture.py` by hand: the build makes the database again only when one of those files changed, and otherwise keeps it in under a second. The gate's own run then keeps the database the drill built.

Ticket 49's rehearsal timed each change a second time: each drill was worked through once, without a timer, while its entry here was written. Its times measure making a known change and the gate's run. To measure how long a new change takes, pick an example nobody has tried yet and start the timer when you read the request.

The live part of each drill, under "On the workspace", runs later, one step at a time, from the main checkout with its `.env`.

## 1. Add a data source

- **The one place.** `config/sources.toml`
- **Proved by.** `tests/test_ground_truth.py`, `test_ground_truth`, on its case `every_source_holds_the_rows_its_api_reported`, which step 4 gives the new source's `<key>,true` line. It shows the fixture database holds every row the source's API reported. `tests/test_config.py`'s `test_a_source_is_one_entry_in_the_registry` shows the change is one entry.
- **Rehearsed with.** The Logistics Performance Index, the Indicators API's overall score `LP.LPI.OVRL.XQ`, as the source `lpi`.

**Steps.**

1. Before the timer, because it needs the network: record the source's pages for the offline gate. Add a `[datasets.<key>]` line of attribution and a `[[source]]` entry to `data/fixture/sources.toml`, then run `uv run python -m strata.fixture.record --only <part of the file name> --write`.
2. Add `[sources.<key>]` to `config/sources.toml`, with its endpoint, watermark field, cadence, license, dataset name, data source, catalog address and the day you checked the name, and one `[[sources.<key>.readiness]]` row for the Data readiness page. A source the Indicators API serves uses the `indicators` silver transform. Any other source adds one module to `src/strata/lakehouse/silver/`.
3. Add the source's size at full scale to `FULL_SCALE` in `tests/test_structured_sources.py`: the total its API reports for every country, times its indicators.
4. Add `-- expect: <key>,true` to `tests/ground_truth/every_source_holds_the_rows_its_api_reported.sql`, in the alphabetical order of the others.
5. Run `uv run --frozen python gates/build_fixture.py`, then `uv run --frozen python tests/record_api.py`, which writes the Data tab's answers again with the new row.
6. At 390 px the Data page's loading state draws each source's card at the average height of today's cards, `CARD_HEIGHT.sources` in `web/src/components/ReadinessTable.tsx`, and `web/tests/data.spec.ts` allows the page to move 16 px when the measures arrive. One more card can move it further. If that test fails, set the height to the cards' new average, which was 16.29rem with the LPI's card.
7. Commit.

Write the dataset name without a number in it. The proposal's Annex 3 credits every dataset by name, and its number check reads a numeral such as the 1 and 5 in the Indicators API's own name, "Logistics performance index: Overall (1=low to 5=high)", as a figure with no source.

**On the workspace.** Deploy the bundle with `uv run --script ops/bundle/deploy.py --env-file .env`, and let the nightly job fetch the source, or run the job. Then `uv run --script ops/bundle/check.py same-rows --env-file .env` runs the ground-truth query on the warehouse, and its `<key>,true` row shows that the source holds every row its API reported.

## 2. Add a tool

- **The one place.** `config/tools.toml`
- **Proved by.** `tests/test_tools.py`, `test_adding_a_tool_is_one_entry_and_the_agents_tool_list_grows_with_it`
- **Rehearsed with.** `package_notices`, which lists every notice published for one package, by its STEP reference.

**Steps.**

1. Add `[tools.<name>]` to `config/tools.toml`: its description, its adapter as `module:function`, the id of its benchmark question, the sources it reads, a `[[tools.<name>.parameters]]` table for each parameter, an optional `as_of` among them, and its `[tools.<name>.result]` with its row fields, source fields, own fields, reason codes and abstentions.
2. Write the adapter, `src/strata/tools/<name>.py`, and its SQL under `src/strata/tools/sql/<name>/`. Every query names its tables in three parts and binds its values, and every row carries its evidence id, its public date and its source line.
3. Add the tool's benchmark question to `evals/benchmark.yaml` in the same change (CLAUDE.md rule 4), with an expected answer that `tests/ground_truth/values.toml` holds.
4. Add a reader of its answer to `ANSWERS` in `src/strata/evals/answers.py`, which both gates use to compare the tool's result with the expected answer.
5. When a screen shows the tool's reason codes, add a sentence for each to `web/src/copy.ts`. A code the tool can return that `config/tools.toml` does not list makes the registry refuse the result, so the page answers HTTP 500.
6. Commit.

**On the workspace.** `uv run --script ops/agent/sync.py --env-file .env` gives the Foundry agent the new tool, and a second run reports no difference. Then `uv run --with azure-identity python ops/evals/full_gate.py --env-file .env` asks the new question of the live agent.

## 3. Change a signal threshold

- **The one place.** `config/thresholds.toml`
- **Proved by.** `tests/test_project_signals.py`, `test_raising_the_needs_a_look_count_above_four_turns_p156634_to_watch_with_no_code_change`
- **Rehearsed with.** `[signals] look_min` from 3 to 4, so a project needs four signals, or one strong one, to need a look.

**Steps.**

1. Change the value in `config/thresholds.toml`.
2. Run `uv run --frozen python gates/build_fixture.py`, then `uv run --frozen python tests/record_home_api.py` and `uv run --frozen python tests/record_following_api.py`. The Home and Following answers carry the thresholds they used.
3. `web/tests/following.spec.ts` types the Status column's definition, which names the number in words. Change "three" to "four" in both places it does.
4. Commit.

A threshold that changes a mark on the demo plan also changes the benchmark answers and the screen tests that state the mark. For example, `[plan_check] completion_passed_min_estimated_usd` above 2,000,000 would turn NWWDA-WSDP-03-2019-2020 in the agency's plan of April 21, 2021 from Needs a look to Watch. KE-NWWDA-541055-CW-RFB is moved on since the plan whatever the threshold is, because the contract awards say its contract was signed.

The rehearsal's value changes no outcome on the fixture. A value that changes which projects need a look, or which signals fire, also changes four tests that state those outcomes: `tests/test_project_signals.py`, `tests/test_mission_brief.py`, `tests/test_hazard.py` and `tests/test_signals_track.py`. Run them after step 2 and change each expected outcome the new value moves, with the project and the signal it names.

A new signal is a check added to `src/strata/tools/project_signals.py`, not a threshold. A check that can fail to run takes its reason from `NOT_RUN` in that file, and `tests/test_project_signals.py` fails when a reason there is missing from `config/tools.toml` or from the Following page's words, so the gate finds it before the live page would answer HTTP 500.

**On the workspace.** The tool's description names `{signals.look_min}`, so run `uv run --script ops/agent/sync.py --env-file .env`. Then deploy the App, which reads the file when it starts: `uv run --script ops/app/deploy_app.py --env-file .env --keep-secrets`.

## 4. Add a country to the slice

- **The one place.** `config/slice.toml`
- **Proved by.** `tests/test_fetch.py`, `test_the_notices_fetch_asks_for_each_slice_country_on_its_own_with_its_own_watermark`. It reads the slice and checks that the nightly fetch asks for every country's notices, the new one included. `tests/test_config.py`'s `test_adding_a_country_to_the_slice_is_one_entry` shows the change is one entry.
- **Rehearsed with.** Nepal, `NP` and `NPL`.

**Steps.**

1. Add a `[[countries]]` entry with the country's name and its two ISO codes. The nightly fetch of the notices and the monthly loan history follows this list, so `config/sources.toml` needs no change.
2. Run `uv run --frozen python gates/build_fixture.py`, then `uv run --frozen python tests/record_api.py` and `uv run --frozen python tests/passage_rows.py`. The slice's data readiness sentence names every country, and `tests/passage_rows.py` writes the hash of those rows again.
3. `web/tests/shelf.spec.ts` types the slice's countries in full. Add the new one.
4. Commit.

The Data page's 390 px test allows the page to move 16 px when its measures arrive. A longer country name than Nepal, such as Ethiopia, makes the slice's sentence take one more line in three of the source cards, and that test fails.

**On the workspace.** Deploy the bundle. The next nightly run fetches the country's notices and monthly loan history, and its parse_and_embed task reads its projects' documents under the daily page cap. `uv run --script ops/bundle/check.py job-run --env-file .env` shows the run finished.

## 5. Swap the model

- **The one place.** `config/models.toml`
- **Proved by.** `tests/test_agent_sync.py`, `test_swapping_the_agents_model_is_one_line_and_the_next_sync_changes_only_its_model`
- **Rehearsed with.** The agent role, from `gpt-5.4-mini` to `gpt-4.1-mini`.

**Steps.**

1. Change the role's `deployment` line.
2. Commit.

Give each role a deployment of its own. Azure caps tokens per minute for each deployment, so two roles on one deployment share one cap, and the day-one probe's test fails.

**On the workspace.** Deploy the model in Azure with its cap through the wizard, `bash ops/wizard/strata-setup.sh`, which reads the name from the model file. Then run `uv run --script ops/dayone/probe_caps.py --env-file .env`, which reads the cap back, `uv run --script ops/agent/sync.py --env-file .env`, which moves the Foundry agent to the new deployment, and the App deploy.

## 6. Reorder the evidence ladder

- **The one place.** `config/evidence_ladder.toml`
- **Proved by.** `tests/test_get_disagreements.py`, `test_reordering_the_ladder_in_its_config_flips_the_side_strata_leans_on`
- **Rehearsed with.** The two ties, the more recent source before the more specific one.

**Steps.**

1. Change `order` under `[ties]`.
2. `tests/test_config.py`'s `test_the_evidence_ladder_orders_outcome_judgments_then_moments_then_the_two_ties` states PLAN.md section 5's order. Change its ties line to the new order.
3. `tests/test_get_disagreements.py`'s `test_a_tie_between_records_goes_to_the_more_specific_source` states which side KE-NWWDA-199461-GO-RFB's signing date leans on. With the recent source first, it leans on the October 9, 2026 plan row, by the rule `tieRecent`.
4. Commit.

Reordering the outcome rule's tiers instead, such as the ICR before IEG's review, changes which side P130164's ratings lean on. The project timeline's and the view switch's recordings, and the tests of those disagreements, then change too.

docs/PLAN.md section 5 and the spec describe the ladder in words. When the panel keeps the change, update them as well.

**On the workspace.** The nightly job's detect_disagreements task applies the ladder at its next run. Deploy the bundle, and run the job or wait for the night.

## 7. Add a field to the package form

- **The one place.** `config/package_form.toml`
- **Proved by.** `tests/test_planned_packages.py`, `test_a_field_added_to_the_schema_is_a_chip_in_its_group_and_removing_it_removes_the_chip`
- **Rehearsed with.** Contract Type, STEP's column for consulting packages, as a text field under How.

**Steps.**

1. Add a `[[fields]]` entry: its key, group, kind, source, label, the chip's words while it is empty, and STEP's field name. Its words live in this file, and the copy lint reads them.
2. Run `uv run --frozen python gates/build_fixture.py`, then `uv run --frozen python tests/record_packages_api.py` and `uv run --frozen python tests/record_steps_api.py`. Each planned package's answer carries the form.
3. `web/tests/planned-package.spec.ts` types the wireframe's chips under How. Add the new chip's words, "Add the contract type". A field under What instead goes in the test's What chip lists, the one it types after it removes the lots among them.
4. Commit.

**On the workspace.** Deploy the App. The package reader is asked for the new field with no other change, unless its entry says `asked = false`.

## 8. Reword copy

- **The one place.** `web/src/copy.ts`
- **Proved by.** `web/tests/lint.spec.ts`, `the gate fails when a component renders a string that is not from the copy file`
- **Rehearsed with.** Home's error line, "I couldn't load your briefing because the data service didn't answer.", as "I couldn't load your briefing. The data service didn't answer, so try again in a minute."

**Steps.**

1. Search `web/tests` and `tests/fixtures/api` for the old words first, since screen tests type copy in full. Change each place that types them.
2. Change the string in `web/src/copy.ts`.
3. When the string is one the server keeps a copy of, such as a Data readiness sentence or a draft file's words, run `node web/lint/server-copy.ts --write`.
4. Commit.

**On the workspace.** Deploy the App.

## 9. Add a benchmark or must-refuse question

- **The one place.** `evals/benchmark.yaml`
- **Proved by.** `tests/test_benchmark.py`, `test_a_question_added_to_the_file_is_one_entry_and_the_next_full_gate_asks_and_scores_it`
- **Rehearsed with.** A documents question: which procurement rules P130164's appraisal document said its goods and works would follow, citing the PAD's Annex 3.B, paragraph 21.

**Steps.**

1. Add the question at the end of the file: its id, kind, tool, the question as a person would ask it, the tool's arguments, the expected answer or citations, and its source in `tests/ground_truth/values.toml`.
2. Commit. The gate asks the tool the question on the fixture and checks the expected answer.

A must-refuse question, for a new refusal or for one that has a question already, takes two more steps before the commit:

1. Add a scripted case to `tests/fixtures/agent/cases.toml` that asks the question word for word, and record it from the live agent with `uv run --script ops/agent/record.py --env-file .env`. `tests/test_refusals.py` asks every must-refuse question in the benchmark file through the case that asks it, and checks the refusal key the question expects.
2. A new refusal key also needs its entry in `src/strata/agent/refusals.py`, its sentences in `web/src/copy.ts` and a line in the orchestrator's instructions, which `tests/test_refusals.py` checks.

`tests/test_live_scripts.py` counts the benchmark's must-refuse questions, so the live must-refuse check (`ops/agent/refuse_live.py`) needs no change.

**On the workspace.** `uv run --with azure-identity python ops/evals/full_gate.py --env-file .env` asks every question, the new one too, of the live agent.

## 10. Add a dashboard tile

- **The one place.** `src/strata/dashboard/definition.py`
- **Proved by.** `tests/test_dashboard_pages.py`, `test_adding_a_tile_for_a_kpi_that_exists_is_one_entry_and_removing_it_is_deleting_that_entry`
- **Rehearsed with.** A counter for the KPI that exists as `rolling_coverage`, "Rolling coverage of the 8-in-10 range", on the AI quality page.

**Steps.**

1. Add `Counter("<kpi>", "<kpi>")` to the page's tiles, where it should sit. A counter's name is its KPI's id in `config/kpis.toml`. A new KPI needs its defining query and its copy keys too.
2. Run `uv run --frozen python -m strata.dashboard --write`, which writes the dashboard's file and its test copy.
3. `tests/test_dashboard_pages.py`'s `test_governance_and_ai_quality_hold_the_brief_s_counters_in_order` states the 45 design brief's counters. Add the new one.
4. Commit.

**On the workspace.** Deploy the bundle, which deploys "Prism operations (test)" beside "Prism operations". Open the test copy and check the tile, then keep it or delete its entry and deploy again.
