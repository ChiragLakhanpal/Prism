# The knowledge graph is Unity Catalog tables, not a graph database

Projects, packages, notices, contracts, suppliers, documents, passages, lessons and assertions are Delta tables with declared keys, and the links between strata, such as a contract informed by a completion-report paragraph, are rows in one edge table. Prism's paths are at most four hops, which joins and recursive SQL handle. Search, SQL and the models read the same rows under one set of permissions and one lineage graph, and every row keeps its public date for as-of answers (ADR 0002). For users, the app shows an evidence trail per project (What, How and Why on one time axis) and a one-hop neighbourhood of at most about 20 nodes, not a free-form graph, which stops being readable past about 20 nodes.

## Considered options

- **Neo4j:** a second store to load, sync and secure. As-of answers and lineage would stop at its boundary, and Free Edition may not be able to reach it.

## Consequences

- Whole-graph analysis, such as supplier communities, runs as GraphFrames jobs rather than live queries.
- If paths grow well past four hops, revisit. Neo4j stays in the proposal as the production option.
