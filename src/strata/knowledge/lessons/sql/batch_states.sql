-- Each lesson extraction request's newest row in bronze: whether it is waiting, answered or failed. An
-- answer written in the same instant as its request still comes after it.
SELECT
  b.custom_id,
  b.document_id,
  b.version,
  b.project_id,
  b.batch_id,
  b.model,
  b.status,
  b.output,
  b.recorded_at
FROM strata.bronze.lesson_batches AS b
QUALIFY row_number() OVER (
  PARTITION BY b.custom_id
  ORDER BY b.recorded_at DESC, CASE WHEN b.status = 'submitted' THEN 1 ELSE 0 END
) = 1
