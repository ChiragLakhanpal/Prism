-- The showcase ICR's paragraph 54, the rebidding lesson, as one passage of the AI Search index's source
-- table, written as plain SQL apart from search_passages' own code. search_passages' benchmark question
-- (evals/benchmark.yaml, search-passages-icr-rebidding) expects this passage in its top three.
--
-- The page, section and printed page are tests/ground_truth/values.toml's icr-para-54, read from the
-- ICR of October 10, 2019 (documents API id 31525018), and the 66 PDF pages are the ticket's ("PDF page
-- 23 of 66"). The ICR became public on November 2, 2019 (values.toml, icr-disclosed). Run it on the
-- warehouse after the live run with: uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- param: project_id = P130164
-- param: paragraph = 54
-- expect: passage_id,section_path,pdf_page,pdf_pages,printed_page,parts,public_from
-- expect: 31525018/v1/54,III.B,23,66,19 of 62,1,2019-11-02
SELECT passage_id, section_path, pdf_page, pdf_pages, printed_page, parts, public_from
FROM strata.gold.passage
WHERE project_id = :project_id
  AND document_type = 'Implementation Completion and Results Report'
  AND paragraph = :paragraph
