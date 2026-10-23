"""The document reader: where documents come from, and how their pages are read.

- documents.py  the documents API, each document's published text and the text of each PDF page,
                offline from the recorded fixture and live from the World Bank's hosts.
- layout.py     Route B, the layout parser: the tables on one PDF page, read offline from the
                recorded words and live with ai_parse_document.
- step.py       STEP's Procurement Plan, word for word: its section, column and step names, the
                activity references a plan's text lists, and its tables read into STEP rows.
"""
