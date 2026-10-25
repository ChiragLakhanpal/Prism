-- The edge table: every link between strata in the knowledge model, one row per link (ADR 0004; ticket 22).
-- Each end is named by its evidence id, the table its record lives in and its key, so a reader opens either
-- end in the evidence drawer as it is (strata.gold.contract:OP00044090, strata.gold.passage:31525018/v1/54).
-- Paths are at most four hops, answered by joins and recursive SQL (tests/ground_truth/four_hop_supplier_to_
-- completion_report.sql). The relink task rebuilds it (strata.knowledge.links) from gold/edge.sql.
--
-- kind             what the link says, in strata.knowledge.links.KINDS, the one list: borrows (project to
--                  country), plans (project to package), has (project to contract, document to passage),
--                  advertised_in (package to notice), awarded_as (package to contract), signed_by (contract to
--                  supplier), lists_bidders (award notice to supplier), described_in (project to document) and
--                  appeared_together (contract to passage), the one scored kind. Screens never show a kind's
--                  name: a scored link is always written "appeared together", never as a cause.
-- from_id, to_id   the two ends, as evidence ids
-- from_kind, to_kind   project, country, package, notice, contract, supplier, document or passage
-- project_id       the project the link belongs to
-- score            for appeared_together, the link's score: the sum of its five parts, each at two decimals
-- score_project, score_sector, score_time, score_text, score_mentions
--                  the points each part scored (config/thresholds.toml [links] gives each part's most)
-- months_apart     months between the contract's signing and the document's date, rounded to the nearest
--                  month at 365.25 / 12 days a month; time_direction says whether the document came after,
--                  before or in the same month (same) as the signing
-- sector_code, sector_name   the project's sector with the largest share, which the sector part matched:
--                  TI, Rural and Inter-Urban Roads (the name without its taxonomy year, FY17 - )
-- category         the contract's procurement category, such as Works
-- matched_terms    the words the contract's description and the paragraph share, as a JSON list
-- mentions         what the paragraph mentions of the contract, as a JSON list of {kind, code, text, start, end}:
--                  its STEP reference or another reference (reference), a place in its description (place),
--                  its description (name) or its procurement category (category), with where the words sit
-- scored_on        the day the relink task scored it
-- public_from      the later of its two ends' public dates (ADR 0002), so no link shows before both ends do
CREATE TABLE IF NOT EXISTS strata.gold.edge (
  kind STRING NOT NULL,
  from_id STRING NOT NULL,
  from_kind STRING NOT NULL,
  to_id STRING NOT NULL,
  to_kind STRING NOT NULL,
  project_id STRING,
  score DECIMAL(4, 2),
  score_project DECIMAL(4, 2),
  score_sector DECIMAL(4, 2),
  score_time DECIMAL(4, 2),
  score_text DECIMAL(4, 2),
  score_mentions DECIMAL(4, 2),
  months_apart INT,
  time_direction STRING,
  sector_code STRING,
  sector_name STRING,
  category STRING,
  matched_terms STRING,
  mentions STRING,
  scored_on DATE,
  public_from DATE NOT NULL
)
