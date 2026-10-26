-- The examples the seed command set up for each viewer of the reviewing panel (ticket 41; python -m
-- strata.seed_examples): one row per viewer and example, written once, so running the command again sets nothing up
-- twice, and an example the viewer discarded or unfollowed is not set up again. Home, the Drafts tab and the other
-- screens read it to label each example "Example". Written by the app's own service principal; a row is added only
-- when none exists for the viewer and example (CLAUDE.md rule 5).
--
-- viewer_id    the user id the Databricks App forwards for the viewer
-- example_key  the example, by its key in src/strata/seed_examples.py (EXAMPLE_KEYS): follows, review_notes_demo_plan,
--              package_rural_roads_kenya, ppsd_rows_demo_package or lesson_change
-- item_kind    what it set up: follow, draft, package or lesson_version
-- item_id      that item's id: the project IDs followed (joined by commas), the draft's id, the package's id, or
--              the lesson, the version the draft cites and the example version ({lesson_id}:{cited}:{version})
-- seeded_by    always strata: no person set it up
-- seeded_at    when, in UTC
-- public_from  the day it was set up, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.seeded_examples (
  viewer_id STRING NOT NULL,
  example_key STRING NOT NULL,
  item_kind STRING NOT NULL,
  item_id STRING NOT NULL,
  seeded_by STRING NOT NULL,
  seeded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
