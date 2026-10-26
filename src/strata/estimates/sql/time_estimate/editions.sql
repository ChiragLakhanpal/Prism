-- The time estimate's backtest (ticket 44): the passages of each project's current Project Appraisal Document public
-- by :as_of, in order, from which each project's edition of the procurement rules is read (config/editions.toml;
-- ticket 29's tag), so the backtest can count each edition's unseen packages.
SELECT d.project_id, p.text, p.public_from
FROM strata.silver.passages AS p
JOIN strata.silver.documents AS d ON d.document_id = p.document_id
WHERE d.document_type = 'Project Appraisal Document'
  AND d.replaced_on IS NULL
  AND p.public_from <= :as_of
ORDER BY d.project_id, p.pdf_page, p.passage_id
