-- Each contract and paragraph of its project's reports whose link score reached config/thresholds.toml's
-- links.threshold, with the score's five parts (ticket 22). The relink task writes it (strata.knowledge.links,
-- relink) and keeps only its latest run; gold/edge.sql makes each row an appeared_together edge.
--
-- run_id           the run that scored it
-- contract_id      the contract, as strata.gold.contract keys it
-- passage_id       the paragraph, as strata.gold.passage keys it
-- project_id       the project both belong to
-- score, score_project, score_sector, score_time, score_text, score_mentions, months_apart, time_direction,
-- sector_code, sector_name, category, matched_terms, mentions
--                  as in strata.gold.edge
-- scored_on        the day it was scored
-- public_from      the later of the contract's and the paragraph's public dates (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.contract_passage_links (
  run_id STRING NOT NULL,
  contract_id STRING NOT NULL,
  passage_id STRING NOT NULL,
  project_id STRING NOT NULL,
  score DECIMAL(4, 2) NOT NULL,
  score_project DECIMAL(4, 2) NOT NULL,
  score_sector DECIMAL(4, 2) NOT NULL,
  score_time DECIMAL(4, 2) NOT NULL,
  score_text DECIMAL(4, 2) NOT NULL,
  score_mentions DECIMAL(4, 2) NOT NULL,
  months_apart INT,
  time_direction STRING,
  sector_code STRING,
  sector_name STRING,
  category STRING,
  matched_terms STRING NOT NULL,
  mentions STRING NOT NULL,
  scored_on DATE NOT NULL,
  public_from DATE NOT NULL
)
