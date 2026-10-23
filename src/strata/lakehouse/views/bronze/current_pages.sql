-- The newest page bronze kept for each request: what the source holds now. Bronze keeps every page
-- it was sent, and keeps a page again only when its content changed, so an unchanged page keeps its
-- first fetch day and still counts. A record that a later fetch of the same request no longer holds
-- stays in an older page, which this view leaves out.
-- silver.awards_current and the data readiness measures of rows held read this view, so the rule is
-- written once.
CREATE OR REPLACE VIEW strata.bronze.current_pages AS
SELECT *
FROM strata.bronze.api_pages
QUALIFY row_number() OVER (PARTITION BY source, request ORDER BY fetched_at DESC, page_hash) = 1
