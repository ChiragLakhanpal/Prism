# 138: The Timeline tab and the Connections tab agree on a project's contracts, through one definition

**What to build:** On October 29, 2026 the demo walkthrough's second capture showed P130164 (India roads, closed 2018) saying two things one click apart: its Timeline tab's records lane reads "I have no contract records for this project", while its Connections tab reads "six contracts appeared together with 52 paragraphs from 10 of its reports". The Timeline's records lane (`src/strata/server/timeline.py`, `sql/timeline/signings.sql`) counts contracts from the sources `CONTRACT_SOURCES` names (the contract awards data since FY 2020 and award notices), while the Connections tab (`src/strata/server/connections.py` or its route in `app.py`) reads the project's contracts from `strata.gold.contract` without that filter, so a project closed before FY 2020 has contracts on one tab and none on the other. Define "a project's contracts" once (a registry entry in `config/sources.toml` or the module both read) and use it in both places; where a source is left out, the lane says which ("no contracts from the awards data, which starts in FY 2020; six from the project's reports") rather than "no contract records". Tests on the fixture (P130164 has both kinds), and the live proof is the orchestrator's: both tabs name the same count for P130164 on the App after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `src/strata/server/timeline.py` (the records lane, `CONTRACT_SOURCES`), `src/strata/server/sql/timeline/signings.sql`, the Connections route and its SQL, `src/strata/tools/project_records.py` (how the tool counts contracts), GLOSSARY.md (contract, award).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] One definition of a project's contracts, in one place, read by the Timeline's records lane and the Connections tab (a test that both routes give the same count for every fixture project).
- [ ] Where a source is left out of a lane, the sentence names it instead of saying there are no records (a test on P130164).
- [ ] On the paid workspace, P130164's Timeline and Connections tabs agree after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 21:03 PDT from the walkthrough's second capture.
