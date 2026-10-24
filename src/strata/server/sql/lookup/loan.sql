-- The one box's loan lookup (ticket 14): the project a loan or credit finances, from the project records
-- public by the as-of date. :loan_numbers holds the normalized numbers the typed text can stand for, such
-- as IDA60290, or IDA60290, IBRD60290 and TF60290 for bare digits, joined by commas.
SELECT
  l.loan_number,
  l.loan_number_as_written,
  l.project_id,
  p.project_name
FROM strata.gold.project_loan AS l
LEFT JOIN strata.gold.project AS p ON p.project_id = l.project_id AND p.public_from <= :as_of
WHERE array_contains(split(:loan_numbers, ','), l.loan_number)
  AND l.public_from <= :as_of
ORDER BY l.public_from DESC, l.loan_number
LIMIT 1
