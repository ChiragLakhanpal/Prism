# 137: A package's comparables window never ends before it starts: a plan older than the awards data uses the data's own span

**What to build:** On October 29, 2026 the demo walkthrough's second capture showed, on the India roads package IN-RRSMP-7516-CW-RFB (P130164, plan of June 20, 2018), section 1's note: "They had to be in India and have notices from July 1, 2019 to June 20, 2018", a window that ends before it starts, because `find_comparables` (`src/strata/tools/find_comparables.py`) closes the window at the plan's date while the contract awards data begins with FY 2020 (July 1, 2019). Make the window honest in one place: when the plan's date falls before the data's first notice, the window runs from the data's start to the page's as-of date and the note says so ("The plan is older than the awards data I hold, so I compared packages with notices from July 1, 2019 to October 30, 2026"); when no package can match, the section says why instead of a range. The sentence can never name an end before its start (a test that builds the note for every plan date in the fixture). Tests on the fixture with P130164's package; the live proof is the orchestrator's: the package page reads correctly on the App after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `src/strata/tools/find_comparables.py` (the window and its note), `web/src/components/PastRange.tsx` (the note's copy), `config/tools.toml` (the tool's abstentions), the benchmark question for the tool in `evals/benchmark.yaml` (update it in the same change if the window's wording is part of it, rule 4).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The comparables window never ends before it starts: a plan dated before the awards data's first notice uses the data's start to the as-of date, with a note that says why (tests over every plan date in the fixture, and P130164's package).
- [ ] When nothing can match, section 1 says why instead of a range (a test), and the benchmark question follows the wording if it names the window.
- [ ] On the paid workspace, /packages/IN-RRSMP-7516-CW-RFB reads correctly after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 21:03 PDT from the walkthrough's second capture.
