-- The day each ranked passage became public, whatever date the search was asked as of, so the evaluation can
-- refuse a passage public after its query's date (strata.estimates.retrieval). :ids holds the passage ids
-- joined by commas, which no passage id contains.
SELECT passage_id, document_id, public_from
FROM strata.gold.passage
WHERE array_contains(split(:ids, ','), passage_id)
