"""The tags a route carries, read by the screen tests through the router.

MODEL marks every route that calls a model: the answer stream, the draft writers, the package reader, the lesson
writer's rewrite, and the routes that run the criteria reader or the verifier's judge. A project's Summary, Home, the
Timeline and the contract trail must render without a request to one (ticket 21), and their screen tests check that
against the list strata.server.app.model_routes() gives, recorded in tests/fixtures/api/model-routes.json.
"""

MODEL = "model"
