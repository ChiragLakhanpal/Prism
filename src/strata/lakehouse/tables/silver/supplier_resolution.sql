-- The supplier each supplier row resolves to, for the sources whose rows may lack a STEP supplier ID
-- (ticket 19; docs/PLAN.md section 5): every awarded bidder of an award notice
-- (strata.silver.notice_bidders) and every row of the FY2001 to FY2016 awards
-- (strata.silver.awards_fy2001_2016), whose dataset has no supplier_id column. The awards since FY2020
-- give every row its STEP supplier ID, so gold reads them directly. strata.knowledge.suppliers.resolve
-- writes it in the nightly job's bronze_to_gold task, before gold, and keeps only its latest run.
--
-- A STEP supplier ID decides first: a row that has one resolves to it and never enters name matching.
-- A row with no ID is matched by name within its country, and joins a supplier only through a pair in
-- strata.ops.supplier_pairs that merged. A row for a person hired as an individual consultant is never
-- matched and never named.
--
-- run_id                 the nightly run that resolved it; only the latest run's rows are kept
-- source                 notices or awards_fy2001_2016
-- source_key             the notice ID, or the contract number of the FY2001 to FY2016 row
-- position               the row's place among its contract's suppliers: the awarded bidder's place
--                        on the notice, or, for the FY2001 to FY2016 awards, its place once a row
--                        that names a joint venture's members ("X IN JV WITH Y") is read as one row
--                        per member
-- contract_id            the contract it belongs to in strata.gold.contract (the contract number, or
--                        the notice ID for a contract known from its award notice)
-- project_id             the row's project
-- name                   the supplier's name as the row writes it; empty for an individual consultant
-- country                the supplier's country as the row writes it
-- step_supplier_id       the STEP supplier ID the row writes, when it writes one
-- individual_consultant  true for a person hired as an individual consultant
-- supplier_id            the supplier it resolves to: its STEP supplier ID; the STEP supplier ID of
--                        the supplier its name merged with; or N- and a key of its own for a supplier
--                        known only by name. Empty for an individual consultant with no ID.
-- joint_venture_id       the joint venture it is a member of on this contract: JV- and its members'
--                        supplier IDs, as strata.gold.contract keys one. Empty when it signed alone.
-- resolved_on            step_supplier_id, name (it merged with another row by name), unmatched (it
--                        is a supplier of its own, known by name) or individual_consultant
-- public_from            the row's public_from (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.supplier_resolution (
  run_id STRING NOT NULL,
  source STRING NOT NULL,
  source_key STRING NOT NULL,
  position INT NOT NULL,
  contract_id STRING,
  project_id STRING,
  name STRING,
  country STRING,
  step_supplier_id STRING,
  individual_consultant BOOLEAN NOT NULL,
  supplier_id STRING,
  joint_venture_id STRING,
  resolved_on STRING NOT NULL,
  public_from DATE NOT NULL
)
