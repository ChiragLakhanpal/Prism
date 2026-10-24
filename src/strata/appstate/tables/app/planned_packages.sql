-- One row for each package a person started planning from a sentence (ticket 15), saved only once the
-- package reader read the sentence (or the person chose to set the criteria themselves), so a failed
-- model call leaves nothing here. It is app state, so it lives in Lakebase (ADR 0005), in the app state
-- database's schema app; src/strata/appstate says how the app reaches it. The plan-a-package workflow
-- (src/strata/packages) writes it as the app's own service principal, and every read shows a package only
-- to the person who made it. Its criteria are its latest row in strata.app.planned_package_saves.
-- Nothing deletes a package.
--
-- Packages render as they are today, so no read filters them by public_from.
--
-- package_id   the package's id, in its address: /packages/pkg-...
-- author_id    the user id the Databricks App forwarded for the person who made it
-- author_name  their name as the App forwarded it
-- sentence     the sentence they wrote, shown as "You wrote" for the life of the package
-- run_id       the package reader's run in strata.ops.agent_runs, or empty when the person set the
--              criteria themselves
-- created_at   when it was first saved, in UTC
-- public_from  the day it was first saved, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.app.planned_packages (
  package_id STRING NOT NULL,
  author_id STRING NOT NULL,
  author_name STRING,
  sentence STRING NOT NULL,
  run_id STRING,
  created_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
