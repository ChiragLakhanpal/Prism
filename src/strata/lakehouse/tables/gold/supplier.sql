-- A supplier, by its STEP supplier ID only. Matching suppliers by name comes later (ticket 19).
--
-- supplier_id   the STEP supplier ID, or JV- and its members' IDs for a joint venture
-- name          the firm's name, or its members' names for a joint venture. Empty for an individual
--               consultant: the awards dataset names them only as INDIVIDUAL CONSULTANT, and Strata
--               never names a person (spec, user story 115).
-- kind          firm, joint venture, or individual consultant
-- member_count  how many members a joint venture has; 1 for anyone else
-- public_from   the earliest public_from of its contracts (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.supplier (
  supplier_id STRING NOT NULL,
  name STRING,
  country STRING,
  kind STRING NOT NULL,
  member_count INT NOT NULL,
  public_from DATE NOT NULL
)
