"""Drafts: what Prism writes for a person to check and export, and nothing leaves without them (ticket 35).

- store.py keeps drafts, their states, their exports and their files in strata.ops.
- runtime.py writes a draft (the kind's workflow reads its facts, the writer agent writes, the verifier
  checks every sentence, and only then is it saved), moves it between states on its author's acts, and
  builds what the draft page and the Drafts tab show.
- review_notes.py is the check-a-plan workflow: review notes on a borrower's Procurement Plan.
- files.py makes the export's files: the Word file with its sources as footnotes, and the evidence pack's
  PDF and CSV. Prism sends nothing itself; the files go only to the person's browser.
- holds.py says what keeps a draft from export, for the holds in config/drafts.toml.

The words of the files come from web/src/copy.ts through copy.json beside this file, which
node web/lint/server-copy.ts --write writes.
"""
