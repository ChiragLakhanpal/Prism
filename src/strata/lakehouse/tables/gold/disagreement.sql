-- A disagreement: two assertions about the same subject and attribute, for the same or an overlapping
-- period, that cannot both be true (GLOSSARY.md). Assertions about different periods form a trajectory
-- instead, and are never here. Both sides stay in strata.gold.assertion. Written by the nightly job's
-- detect_disagreements task (src/strata/knowledge/assertions.py), rebuilt for each project of the run,
-- with the side the evidence ladder (config/evidence_ladder.toml) leans on.
--
-- disagreement_id      stable: a hash of the two assertion ids
-- first_assertion_id   the side written first (made_at, then public_from)
-- second_assertion_id  the side written second
-- period_event, period_start, period_end   the period both describe: where the two periods overlap
-- lean_assertion_id    the side Prism leans on; empty when the ladder ranks both the same
-- rule_id              the ladder's rule that decided: outcome, moment, tieSpecific or tieRecent
-- replaced_on          the earlier day a later version replaced one of its sides; from then on it is not
--                      a current disagreement
-- public_from          the later side's public date: the day both were public (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.disagreement (
  disagreement_id STRING NOT NULL,
  project_id STRING NOT NULL,
  subject_kind STRING NOT NULL,
  subject_id STRING NOT NULL,
  attribute STRING NOT NULL,
  first_assertion_id STRING NOT NULL,
  second_assertion_id STRING NOT NULL,
  period_event STRING NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  lean_assertion_id STRING,
  rule_id STRING,
  replaced_on DATE,
  public_from DATE NOT NULL
)
