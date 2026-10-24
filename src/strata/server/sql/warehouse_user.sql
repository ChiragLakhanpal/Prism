-- Who the warehouse says ran this query. GET /api/me/warehouse runs it with the viewer's own
-- token, so two people who open the deployed app each see their own name here (ticket 06).
SELECT current_user() AS warehouse_user
