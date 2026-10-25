-- The labeled passages of a bilingual query (evals/bilingual_queries.toml) that the documents hold and that were
-- public before the query's date, with their documents (strata.knowledge.retrieval.labels). :ids holds the passage
-- ids joined by commas, which no passage id contains.
SELECT passage_id, document_id
FROM strata.gold.passage
WHERE array_contains(split(:ids, ','), passage_id)
  AND public_from < :before
  AND (replaced_on IS NULL OR replaced_on >= :before)
ORDER BY passage_id
