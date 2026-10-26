-- Tile 21: who read Strata's tables, by day, person, way in and table, in the dates chosen, from the workspace's
-- lineage system table (system.access.table_lineage), where Free Edition lets Strata read it. It shows which tables
-- were read and how many statements read them, never the text of a query, because a query can carry a person's
-- question. The app runs each query as the person using it through the SQL warehouse, which records no entity, so a
-- read with no entity is the app's. The deploy checks whether the table can be read (docs/workspace-catchup.md).
WITH reads AS (
  SELECT
    l.event_date,
    l.created_by,
    CASE
      WHEN l.entity_type IS NULL THEN 'app'
      WHEN l.entity_type LIKE '%GENIE%' THEN 'genie'
      WHEN l.entity_type LIKE '%DASHBOARD%' THEN 'dashboard'
      WHEN l.entity_type LIKE '%QUERY%' THEN 'sql_editor'
      WHEN l.entity_type = 'NOTEBOOK' THEN 'notebook'
      WHEN l.entity_type IN ('JOB', 'PIPELINE') THEN 'job'
      ELSE 'other'
    END AS through_key,
    l.source_table_full_name,
    l.statement_id
  FROM system.access.table_lineage AS l
  WHERE l.source_table_catalog = 'strata' AND l.event_date BETWEEN :date_from AND :date_to
)
SELECT
  event_date AS day,
  created_by AS person,
  :through_label__through_key AS through,
  source_table_full_name AS table_read,
  count(DISTINCT statement_id) AS queries
FROM reads
GROUP BY event_date, created_by, through_key, source_table_full_name
ORDER BY day DESC, person, through, table_read
