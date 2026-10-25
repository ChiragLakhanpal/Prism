-- A project's timeline (ticket 23): the passages of the project's reports that hold an event's words, such as
-- "mid-term review date" or "restructured", public on the as-of date and not yet replaced then (ADR 0002),
-- earliest public first. The timeline reads the event's date from the first one that gives it.
SELECT
  p.passage_id,
  p.document_id,
  p.document_type,
  p.text,
  p.public_from
FROM strata.gold.passage AS p
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
  AND (p.replaced_on IS NULL OR p.replaced_on > :as_of)
  AND instr(lower(p.text), :words) > 0
ORDER BY p.public_from, p.document_date, p.passage_id
