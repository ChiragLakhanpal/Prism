# 121: The nightly's contacts check flags every pattern the stripper removes, from the stripper's own registry

**What to build:** On October 28, 2026 the live check of ticket 63's step 4 found 53 notices in `strata.silver.notices` whose text still names a person after "Attention" and a title, all from the first fetch of October 26, after a nightly run with ticket 63's stripper deployed. The stripper (`strata.lakehouse.contacts`) removes a name after "Attention" and a title since ticket 63, but the nightly's quality check `contacts_left` (`src/strata/lakehouse/quality.py`) flags only the two patterns it carries, `contacts.LEFT_EMAIL` and `contacts.LEFT_PHONE`, and the notices transform re-reads only the pages that check flags (`src/strata/lakehouse/silver/notices.py`, `contacts_left`), so a page whose only leftover is an "Attention" name is never read again, and every later rule the stripper gains has the same gap. Rule 4 (one source of truth per definition): the check and the re-read must take their patterns from the one registry the stripper removes with, so that a rule added to the stripper is flagged, measured in `strata.ops.data_quality` (the `contacts_left` result) and re-read on the next run without a second edit. Give `strata.lakehouse.contacts` one list of leftover patterns, each the SQL form of a removal rule the last pass takes out (email, labelled phone, a name after Attention and a title, and whatever else the stripper's last pass removes), with a test that every removal rule has its leftover pattern and that each pattern finds the text its rule removes on the fixture; `quality.contacts_left_params` and the notices transform's `contacts_left` read that list; the readiness measure `contact_details_removed` is unchanged. The step 4 query of the catch-up block "Ticket 63, step 4 of 5 ran" is the live check: after the merge, the bundle deploy and the next nightly run, it returns 0 (the orchestrator records it).

Read first: `src/strata/lakehouse/contacts.py` (the removal rules, `LEFT_EMAIL`, `LEFT_PHONE`, `ATTENTION`), `src/strata/lakehouse/quality.py` (`contacts_left_params`, `check_table`), `src/strata/lakehouse/silver/notices.py` (lines 36 to 80, the re-read of flagged pages), `tests/test_contacts.py` and the quality tests, the catch-up block "Ticket 63, step 4 of 5 ran" of October 28, and ticket 76 (the first targeted re-read).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P4
**Design review:** no

- [ ] One registry in `strata.lakehouse.contacts` holds each removal rule's leftover pattern; a test proves every rule of the last pass has one and that each pattern matches on the fixture what its rule removes.
- [ ] `quality.contacts_left` and the notices transform's re-read use that registry; on the fixture, a notice whose only leftover is a name after "Attention" is flagged and read again on the next pass (a test proves the page is read twice).
- [ ] On the paid workspace, after the merge, the bundle deploy and the next nightly run, the step 4 query of ticket 63 returns 0 and `strata.ops.data_quality` holds the night's `contacts_left` count (recorded in the catch-up file under this ticket).

## Comments

- October 28, 2026, orchestrator: opened at 03:45 PDT on the orchestrator's judgment from ticket 63's step 4 live check (the 53 pages are re-read by hand tonight); it builds in wave 4u.
