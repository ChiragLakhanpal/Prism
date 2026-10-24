# 20: Assertions, disagreements and the evidence ladder

**What to build:** Ratings, dates and amounts from records and documents become dated assertions; Strata detects disagreements between them, tells trajectories apart, and applies the evidence ladder to choose the assertion it leans on while keeping both. Assertions come from ISR ratings (each for its own date and period), ICR ratings and narrative accounts (such as ¶78's account of the mid-term review), ICR Review and PPAR ratings, PAD appraisal ratings, the IEG ratings dataset, and contract and plan dates and amounts. Assertions read from text come from the batch model and are rejected unless their quote is found word for word on the cited page. A disagreement is two assertions with the same subject and attribute for the same or an overlapping period whose values cannot both be true; assertions about different periods form a trajectory. The evidence ladder is one config: outcome judgments lean on the ICR Review or PPAR, then the ICR, then the last ISR, then the PAD; assertions about a moment lean on the record made at that moment; ties go to the more specific source, then the more recent; a report re-issued under the same number replaces its earlier version. The get_disagreements tool (one registry entry) returns, for a subject, each disagreement with both sides in the order written, the source Strata leans on, the rule in one sentence, and what changes if the other is kept, plus any trajectories.

Read first: docs/PLAN.md section 5 (Assertions and disagreements); ADR 0002; the blueprint's "When reports disagree, both stay on screen"; docs/agents/areas/knowledge.md.

**Blocked by:** 18 (The document slice, the page router's Route B and the stress shelf)

**Status:** done
**Area:** knowledge
**Phase:** P2
**Design review:** no

- [ ] For P130164, ISR 7 (August 26, 2016, progress towards the objective rated Satisfactory) and ICR ¶78 (October 10, 2019, the mid-term review found part of the objective compromised) come back from get_disagreements as one disagreement, with Strata leaning on the ICR under the outcome-judgment rule.
- [ ] ISRs 1 to 9 (Satisfactory), 10 and 11 (Moderately Satisfactory) and 12 and 13 (Moderately Unsatisfactory) come back as a trajectory, not a disagreement.
- [ ] As of October 1, 2019, no disagreement is returned for that subject, because the ICR was not yet public.
- [ ] Reordering the ladder in its config, with no code change, flips the source Strata leans on in the fixture case.
- [ ] A fixture tie is decided by the more specific source, and a second by the more recent one.
- [ ] The May 4, 2023 re-issue of the ICR Review replaces the March 27, 2020 version for current answers.
- [ ] An extracted assertion whose quote is not on its cited page is rejected and counted.
- [ ] Every assertion has subject, attribute, value, period, made-at date, public_from, source document and passage, and evidence tier, checked by a schema test.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/20-assertions-disagreements-evidence-ladder, as soon as ticket 18 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
- October 24, 2026, merger: merged into build/strata as merge commit da1ab20 (parents dd5cad7 and d8b29dd, so the branch's history is kept). The history scan found no keys. Git merged it with no conflicts. The branch changes no package files and not `gates/steps.toml`, and `scripts/install` ran before the commit anyway. The worktree that built it was `.claude/worktrees/wf_a1d03afa-56c-44`; I removed it after this commit, and the branch stays.
  - **The gate.** Git ran it before the merge commit, and it passed in 92.6 seconds at a load average near 73. By hand on build/strata after the merge, it passed in 71.0 seconds and finished at about 12:47: the Python tests took 55.9, Playwright 47.5, and the wizard and day-one tests 43.1. Ticket 43 is already asked to bring it back under a minute.
  - **Evidence.** Three rounds. Review r3 (`.notes/20-review-r3.md`) approved with 0 blocking and 9 polish findings; round 2's three blocking findings (sides not citable, a run with no batch model deleting the text assertions, one failed answer blocking its report) are fixed. Verify r3 (`.notes/20-verify-r3.md`) passed all eight criteria on the fixture:
    - get_disagreements for P130164 returned one `pdo_progress` row: ISR 7 (`26733307/v1/s4`, Satisfactory, made 2016-08-26, 3 months after the mid-term review) against ICR paragraph 78 (`31525018/v1/78`, PDF page 27, public 2019-11-02, 40 months after), leaning on paragraph 78 under the `outcome` rule. The verify round checked each value against the recorded files.
    - ISRs 1 to 13 came back as one trajectory: Satisfactory 1 to 9, Moderately Satisfactory 10 and 11, Moderately Unsatisfactory 12 and 13. No pair with both sides in the isr tier is a disagreement.
    - As of 2019-10-01, 2019-10-10 and 2019-11-01, no disagreement; on 2019-11-02 it appears. A sweep of 7 subjects over 965 as-of dates (5,531 rows) found 0 items from a document not yet public.
    - The full run on edited copies of `config/evidence_ladder.toml` flipped the lean to ISR 7 when the isr tier was moved above the icr tier, and swapping the ties moved both tie rows, with no code change.
    - KE-NWWDA-199461-GO-RFB leans on the record under `tieSpecific`; KE-MOWASCO-307378-GO-RFB leans on notice OP00216847 under `tieRecent`.
    - The May 4, 2023 ICR Review (34056616) replaces the March 27, 2020 version (31906731): from 2023-05-04 no row or side cites 31906731, and its assertions carry `replaced_on` 2023-05-04.
    - The planted rating (31525018/v1/45) is rejected as `quote_not_on_page` and counted (`rejected.count` 1). Eight doctored quotes were each rejected with the right reason; extra spaces are tolerated.
    - The schema test passed, and a query over all 1,261 assertions found 0 empty required fields.
    - The ticket's own tests (`tests/test_get_disagreements.py`, `tests/test_assertions.py`) took 2.56 seconds; the suites it touches gave 902 passed.
  - **Parked criteria.** The live halves of criteria 1 and 7 (the live batch model), the same rows on the warehouse, the re-recording from a live batch, and B2 on the workspace.
  - **Workspace results.** Nothing ran. `guard.py --env-keys` showed all ten keys set, but the header of `docs/workspace-catchup.md` tells a merger not to run workspace steps while the user runs the backlog by hand today. I parked four blocks there, in the order to run them: "Ticket 20, step 1 of 4" (the live batch run; it needs a redeploy from da1ab20 first, because this merge adds `strata.bronze.batch_answers`, `strata.gold.assertion`, `strata.gold.disagreement` and `strata.ops.assertion_rejections`), step 2 (the same run the morning after a nightly run, for B2), step 3 (`check.py same-rows`, including `p130164_isr_7_against_icr_paragraph_78.sql`) and step 4 (the `--record` run, then the gate). Steps 1 and 4 call Azure's Batch API with the batch role's gpt-5.4-nano, which day-one test 8 found deployed as GlobalStandard, so they will likely stop with exit 2 until decision 2 in `docs/STATUS.md` is answered.
  - **Parked decisions for the user.**
    1. Replay older answers when a request changes (review F5). Should a nightly run with no live model replay the newest answer held for a report even when the ladder's attributes or the passages changed since? Every quote is checked again on its page, so an old answer can only lose assertions. The reviewer suggests yes. Until you choose, the build keeps answers only for unchanged requests, so a ladder change drops paragraph 78 and the showcase disagreement until the live model runs again.
    2. The amount tolerance. `config/thresholds.toml` `[disagreements] amount_tolerance_share = 0.001` (0.1 percent), with a comment for you to confirm. KE-KIMAWASCO-141042-CW-RFB's 0.003 percent gap is not a disagreement; KE-KIMAWASCO-142995-CW-RFB's 2.6 percent gap is.
    3. What "more recent" means for an awards record. `made_at` is the contract's signing date, so for KE-MOWASCO-307378-GO-RFB the award notice published March 3, 2023 wins the tie. The build keeps this.
  - **Follow-ups, not blocking.**
    1. Verify V1 and review F3, fix before ticket 43 or before the live agent cites a side: a side's passage text bypasses Prompt Shields. `src/strata/tools/sql/get_disagreements/assertions.sql` selects `p.text` with no attack filter; select `CASE WHEN p.attack_detected THEN NULL ELSE p.text END`.
    2. Review F1: a cited side has no source line, so its evidence card on the Ask screen would read ", paragraph 78". Share search_passages' source builder with get_disagreements.
    3. Review F2: a sentence citing only a passage side for a number is removed; the tool description should tell the agent to cite the row as well.
    4. Review F4 and F6, for ticket 43: a request missing from a resumed batch's output waits for ever, a failed `GET /batches/<id>` stops the run, and the live run sends one batch per project, each waiting up to an hour.
    5. Review F7 to F9: a later search_passages row replaces a side's record in the turn's facts, "fact" in two comments, and the PAD's document type written twice.
    6. Verify V2 to V4: a lowercase STEP reference gives `unknown_subject`; the rejection codes `passage_not_found`, `value_not_on_scale`, `unknown_attribute` and `unknown_period` have no copy and are not listed in `config/tools.toml` (ticket 23 needs a phrase for each if the timeline shows reasons); ISR 34133893 became public the day before its archive date.
