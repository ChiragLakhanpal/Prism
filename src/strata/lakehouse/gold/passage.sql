-- strata.gold.passage: each passage that has a vector, with its document (or, for a notice's text, its
-- notice), its project and what Prompt Shields found, taking each text's newest vector and newest scan. The passage reader syncs it after
-- embedding (src/strata/lakehouse/passages.py), so it is not in ORDER, which the nightly job's
-- bronze_to_gold task builds before any passage is embedded.
-- key: passage_id
WITH vector AS (
  SELECT text_hash, model, embedding
  FROM strata.silver.passage_embeddings
  QUALIFY row_number() OVER (PARTITION BY text_hash ORDER BY embedded_at DESC, model) = 1
),
scan AS (
  SELECT text_hash, shield, attack_detected
  FROM strata.silver.passage_shields
  QUALIFY row_number() OVER (PARTITION BY text_hash ORDER BY scanned_at DESC, shield) = 1
),
notice AS (
  SELECT n.notice_id, n.notice_date
  FROM strata.silver.notices AS n
  WHERE n.notice_id IN (SELECT document_id FROM strata.silver.passages WHERE kind = 'notice_text')
  QUALIFY row_number() OVER (PARTITION BY n.notice_id ORDER BY n.fetched_at DESC) = 1
)
SELECT
  p.passage_id,
  p.document_id,
  p.project_id,
  pr.project_name,
  pr.country_code,
  c.country_name,
  p.sector,
  p.document_type,
  coalesce(d.document_date, n.notice_date) AS document_date,
  d.report_number,
  p.version,
  p.section_path,
  p.paragraph,
  p.paragraph_numbered,
  p.part,
  p.parts,
  p.pdf_page,
  p.last_pdf_page,
  d.pdf_pages,
  p.printed_page,
  p.language,
  p.parse_route,
  p.kind,
  p.scanned,
  p.table_title,
  p.table_row,
  p.cells,
  p.header,
  p.text,
  p.tokens,
  d.pdf_url,
  d.doc_key,
  CASE WHEN p.kind = 'notice_text'
       THEN concat('https://projects.worldbank.org/en/projects-operations/procurement-detail/', p.document_id)
  END AS notice_url,
  v.embedding,
  v.model AS embedding_model,
  s.shield,
  s.attack_detected,
  d.replaced_on,
  year(p.public_from) * 10000 + month(p.public_from) * 100 + day(p.public_from) AS public_day,
  coalesce(year(d.replaced_on) * 10000 + month(d.replaced_on) * 100 + day(d.replaced_on), 99991231) AS replaced_day,
  p.public_from
FROM strata.silver.passages AS p
LEFT JOIN strata.silver.documents AS d ON d.document_id = p.document_id
LEFT JOIN notice AS n ON n.notice_id = p.document_id AND p.kind = 'notice_text'
JOIN vector AS v ON v.text_hash = p.text_hash
LEFT JOIN scan AS s ON s.text_hash = p.text_hash
LEFT JOIN strata.gold.project AS pr ON pr.project_id = p.project_id
LEFT JOIN strata.gold.country AS c ON c.country_code = pr.country_code
