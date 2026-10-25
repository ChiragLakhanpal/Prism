-- The link scorer's paragraphs (ticket 22): every numbered paragraph of a report the passage reader holds (a
-- passage whose document has a key in its project, so never a notice's text, a table row or a table's summary),
-- leaving out a passage in which Prompt Shields found an attack, as search does.
SELECT
  passage_id,
  project_id,
  sector,
  document_date,
  text,
  public_from
FROM strata.gold.passage
WHERE doc_key IS NOT NULL
  AND kind = 'paragraph'
  AND NOT coalesce(attack_detected, FALSE)
ORDER BY project_id, passage_id
