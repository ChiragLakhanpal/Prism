-- Whether each viewer keeps Home's Start here strip (ticket 41; the 41 design brief, section 4.4): one row each time a
-- viewer removes the examples strip or shows it again, so the latest row says whether it shows. Nothing is updated and
-- nothing is deleted (CLAUDE.md rule 5). Written by the app's own service principal, naming the viewer the Databricks
-- App forwarded, so the choice follows the viewer from browser to browser. Removing the strip leaves the examples
-- themselves alone.
--
-- viewer_id    the user id the Databricks App forwarded
-- visible      false when the viewer removed the strip, true when they showed it again
-- chosen_at    when, in UTC
-- public_from  the day it was chosen, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.start_here_choices (
  viewer_id STRING NOT NULL,
  visible BOOLEAN NOT NULL,
  chosen_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
