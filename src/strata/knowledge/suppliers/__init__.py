"""Suppliers resolved on STEP supplier IDs first, names second (ticket 19; docs/PLAN.md section 5).

- bidders.py   the awarded bidders of each Contract Award notice, read from its plain text
- names.py     supplier names as name matching compares them, and a one-row joint venture's members
- matching.py  Splink's candidate pairs for the rows with no STEP supplier ID, on plain rows
- judge.py     the model that decides the uncertain middle, live and as an offline stand-in
- resolve.py   each supplier row resolved to its supplier, and each candidate pair routed by the
               thresholds file, the model or a person
"""
