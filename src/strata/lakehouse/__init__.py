"""The lakehouse: the engine adapter, the table definitions and the nightly job's tasks.

Modules here import only the standard library at the top, so the nightly job can import them on
serverless compute. DuckDB and sqlglot load inside the functions that need them.
"""
