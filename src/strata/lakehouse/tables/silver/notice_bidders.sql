-- The awarded bidders of each Contract Award notice, in the order the notice lists them, read from
-- strata.silver.notices.notice_text after the fetch removed contact details (ticket 19). Each read
-- of a notice's page adds its rows, so gold reads the rows of each notice's newest page.
-- Evaluation scores, ranks and prices are never kept here: suppliers are never scored or ranked.
--
-- position             1 for the first awarded bidder, 2 for the second, and so on. Several awarded
--                      bidders on one notice are the members of a joint venture.
-- name                 the bidder's name as the notice writes it; empty for an individual consultant,
--                      and for a name the fetch removed as a person's contact detail
-- step_supplier_id     the STEP supplier ID the notice writes in brackets after the name, when it
--                      writes one
-- country              the bidder's country as the notice writes it
-- individual_consultant  true when the notice writes the bidder as Individual Consultant
-- page_hash, fetched_at  the notice's row in strata.silver.notices that was read
-- public_from          the notice's public_from (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.notice_bidders (
  notice_id STRING NOT NULL,
  position INT NOT NULL,
  project_id STRING,
  step_reference STRING,
  name STRING,
  step_supplier_id STRING,
  country STRING,
  individual_consultant BOOLEAN NOT NULL,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
