-- Every bid each Contract Award notice lists, awarded, evaluated and rejected, in the order the notice lists
-- them, read from strata.silver.notices.notice_text after the fetch removed contact details (ticket 22;
-- strata.knowledge.suppliers.bidders, read_bids). Each read of a notice's page adds its rows, so a reader
-- takes the rows of each notice's newest page. The contract trail shows them; ticket 28 can read the
-- rejections. Evaluation scores and ranks are never kept: suppliers are never scored or ranked.
--
-- bid                  1 for the first bid the notice lists, 2 for the second, and so on, across its sections
-- member               1 for a bid by one firm; 1, 2 and so on for the members of a joint venture, which the
--                      notice lists one after another before their one price
-- section              awarded, evaluated or rejected, from the notice's heading over the bid
-- name                 the bidder's name as the notice writes it, without its STEP supplier ID; empty for an
--                      individual consultant, and for a name the fetch removed as a person's contact detail
-- step_supplier_id     the STEP supplier ID the notice writes in brackets after the name, when it writes one
-- country              the bidder's country as the notice writes it
-- individual_consultant  true when the notice writes the bidder as an individual consultant
-- currency             the currency the notice prices the bid in, such as KES
-- price_at_opening     the Bid Price at Opening (or Read Out Price) as the notice writes it, without its
--                      currency: 61503269.60 or 69,826,127.64; empty when the notice leaves it blank
-- evaluated_price      the Evaluated Bid Price (or Final Evaluation Price) as written; empty when blank
-- signed_price         the Signed Contract Price as written, for an awarded bid
-- reason               the Reason for Rejection, word for word, for a rejected bid
-- price_at_opening_label, evaluated_price_label   the notice's own names for the two prices
-- notice_lists_scores  true when the notice lists evaluation scores or ranks, which are left out
-- page_hash, fetched_at  the notice's row in strata.silver.notices that was read
-- public_from          the notice's public_from (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.notice_bids (
  notice_id STRING NOT NULL,
  bid INT NOT NULL,
  member INT NOT NULL,
  project_id STRING,
  step_reference STRING,
  section STRING NOT NULL,
  name STRING,
  step_supplier_id STRING,
  country STRING,
  individual_consultant BOOLEAN NOT NULL,
  currency STRING,
  price_at_opening STRING,
  evaluated_price STRING,
  signed_price STRING,
  reason STRING,
  price_at_opening_label STRING,
  evaluated_price_label STRING,
  notice_lists_scores BOOLEAN NOT NULL,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
