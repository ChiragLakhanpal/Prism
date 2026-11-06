-- A supplier: one record across the contract awards and the award notices (ticket 19; docs/PLAN.md
-- section 5). A STEP supplier ID decides first, and two IDs are never merged by name; only a row with
-- no ID is matched by name, within its country (strata.knowledge.suppliers.resolve). Ticket 22's
-- "signed by" edges and four-hop paths join on supplier_id, so a supplier keeps its key.
--
-- supplier_id   the STEP supplier ID; JV- and its members' supplier IDs for a joint venture; or N-
--               and a key of its own for a supplier known only by name, which keeps the same key
--               while its earliest row does
-- name          the firm's name as its records write it, or its members' names for a joint venture.
--               Empty for an individual consultant: the awards dataset names them only as INDIVIDUAL
--               CONSULTANT, and Prism never names a person (spec, user story 115).
-- kind          firm, joint venture, or individual consultant
-- member_count  how many members a joint venture has; 1 for anyone else
-- resolved_on   step_supplier_id when the supplier, or every member of a joint venture, has a STEP
--               supplier ID; name when the supplier, or any member of a joint venture, is known only
--               by name
-- public_from   the earliest public_from of its rows (ADR 0002)
--
-- No column scores, ranks or rates a supplier.
CREATE TABLE IF NOT EXISTS strata.gold.supplier (
  supplier_id STRING NOT NULL,
  name STRING,
  country STRING,
  kind STRING NOT NULL,
  member_count INT NOT NULL,
  resolved_on STRING NOT NULL,
  public_from DATE NOT NULL
)
