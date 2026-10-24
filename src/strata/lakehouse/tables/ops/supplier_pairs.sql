-- The candidate pairs of name matching for suppliers, and where each one went (ticket 19;
-- docs/PLAN.md section 5). strata.knowledge.suppliers.resolve writes them in the nightly job's
-- bronze_to_gold task and keeps only its latest run. A STEP supplier ID decides first, so a pair
-- always has a row with no ID on its left, and two suppliers with IDs are never a pair.
--
-- Splink gives each pair the probability that its two sides are one supplier, from their names and
-- whether they share a project, and config/thresholds.toml's [supplier_matching] routes it: at or
-- above auto_merge_min_probability it merges; from model_min_probability it goes to the model, which
-- decides merge or no merge when it is sure enough; below that the two stay apart. What stays
-- uncertain goes to a person, through the review list (strata.ops.supplier_review_list). A
-- person's decision (strata.ops.supplier_review_decisions) outranks the thresholds and the model.
--
-- No column scores, ranks or rates a supplier. match_probability and match_weight describe a pair
-- of rows, and only route it.
--
-- run_id              the nightly run that found it
-- pair_id             the left key and the right key, joined by |
-- left_key            a row with no STEP supplier ID: its source key and place, such as 1519849/1
--                     (a contract number) or OP00054114/2 (a notice ID)
-- right_key           a STEP supplier ID, or another row with no ID
-- left_name, right_name            each side's name as its records write it
-- left_country, right_country      each side's country as its records write it
-- left_contracts, right_contracts  each side's contracts, by STEP reference or by contract number or
--                     notice ID, separated by ", "
-- match_probability   Splink's probability that the two sides are one supplier
-- match_weight        the same, as Splink's match weight
-- name_level          how alike the names are once normalized: same_name, same_words,
--                     starts_the_other, nearly_the_same, alike or different
-- projects_level      shared, none_shared or unknown
-- route               where the thresholds and the model sent it: auto_merge, model, person or kept_apart
-- review_reason       why a person must decide it: model_unsure, two_step_supplier_ids or no_model
-- model               the deployment, or the offline stand-in, that judged it
-- model_decision      merge, no_merge or unsure
-- model_confidence    how sure the model said it was, from 0 to 1
-- model_reason        the model's reason, in its words
-- outcome             merge, no_merge, or waiting while it waits for a person
-- decided_by          threshold, model or person
-- reviewer            the user id of the person who decided it
-- decision_reason     the person's reason
-- matched_at          when this run found it, in UTC
-- public_from         the later public_from of its two sides (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.supplier_pairs (
  run_id STRING NOT NULL,
  pair_id STRING NOT NULL,
  left_key STRING NOT NULL,
  right_key STRING NOT NULL,
  left_name STRING,
  left_country STRING,
  left_contracts STRING,
  right_name STRING,
  right_country STRING,
  right_contracts STRING,
  match_probability DOUBLE NOT NULL,
  match_weight DOUBLE NOT NULL,
  name_level STRING NOT NULL,
  projects_level STRING NOT NULL,
  route STRING NOT NULL,
  review_reason STRING,
  model STRING,
  model_decision STRING,
  model_confidence DOUBLE,
  model_reason STRING,
  outcome STRING NOT NULL,
  decided_by STRING,
  reviewer STRING,
  decision_reason STRING,
  matched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
