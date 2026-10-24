-- The stress shelf's outcomes as of the date: every row of the latest document run that recorded them on
-- or before it (strata.ops.stress_shelf), with each document's project name, in the slice file's order.
SELECT
  s.shelf_key,
  s.kind,
  s.position,
  s.state,
  s.document_id,
  s.project_id,
  p.project_name,
  s.document_type,
  s.document_date,
  s.pdf_pages,
  s.pdf_url,
  s.language,
  s.part,
  s.hard_page,
  s.parser_pages,
  s.count,
  s.denominator,
  s.denominator_from,
  s.counted_on,
  s.unreadable,
  s.parts,
  s.parser,
  s.parser_limit_pages,
  s.longest_pages,
  s.read_pages,
  s.daily_page_cap,
  s.run_id,
  CAST(s.measured_at AS DATE) AS measured_on,
  s.public_from
FROM strata.ops.stress_shelf AS s
LEFT JOIN strata.gold.project AS p ON p.project_id = s.project_id
WHERE s.run_id = (SELECT max_by(run_id, measured_at) FROM strata.ops.stress_shelf WHERE public_from <= :as_of)
ORDER BY s.position
