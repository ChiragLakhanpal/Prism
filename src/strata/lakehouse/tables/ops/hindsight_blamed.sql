-- The risks each project's completion report blamed, reconciled from its two codings (ticket 34;
-- src/strata/estimates/hindsight_coding.py). The hindsight test reads the newest row of each project.
--
-- Where the two coders agree on a risk factor, their answer stands. Where they differ, the reading of the ICR
-- Review settles it (rule icr_review). A project with no ICR Review keeps only the risks both coders blamed
-- (rule no_icr_review, a parked rule). When both agree on every factor the rule is agreed. A project whose coders
-- differ while its ICR Review is still unread has no row yet.
--
-- project_id          the project
-- blamed              the blamed risk factors' keys, as a JSON list in the closed list's order; [] when none
-- rule                agreed, icr_review or no_icr_review
-- settled             the factors the coders differed on, as a JSON object of key to blamed or not, as settled
-- coders              the two coders' emails, as a JSON list
-- icr_coding_ids      the two codings reconciled, as a JSON list, and the ICR Review's coding, empty when none
-- review_coding_id
-- reconciled_at       when the row was written, in UTC
-- public_from         the day it was written (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.hindsight_blamed (
  project_id STRING NOT NULL,
  blamed STRING NOT NULL,
  rule STRING NOT NULL,
  settled STRING NOT NULL,
  coders STRING NOT NULL,
  icr_coding_ids STRING NOT NULL,
  review_coding_id STRING,
  reconciled_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
