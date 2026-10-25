-- compare_criteria: the passages of the notices the call reads (:notices, notice ids joined by commas): each
-- section of a notice's scope and qualification text that ticket 18 read into strata.gold.passage (kind
-- notice_text), public on the as-of date and not yet replaced (ADR 0002). A passage in which Prompt Shields
-- found a prompt attack is left out, as search leaves it out. In passage order within each notice.
SELECT
  passage_id,
  document_id AS notice_id,
  project_id,
  section_path,
  language,
  text,
  public_from
FROM strata.gold.passage
WHERE kind = 'notice_text'
  AND array_contains(split(:notices, ','), document_id)
  AND public_from <= :as_of
  AND (replaced_on IS NULL OR replaced_on > :as_of)
  AND coalesce(attack_detected, false) = false
ORDER BY document_id, public_day, passage_id
