"""The knowledge loop for lessons (ticket 29; docs/PLAN.md sections 5 and 11).

- propose.py   the nightly job's propose_lessons task: each current ICR, ICR Review and PPAR goes to the
               batch model once; its proposals are kept only when their quotes are word for word on the
               cited pages; an ICR Review's restatement attaches as a second piece of evidence; each
               passing proposal waits in the review queue.
- batch.py     the batch model behind an adapter: Azure OpenAI's Global Batch live, recorded answers offline.
- review.py    who may recommend, decide and cross-check (the roles file), the business-day clock, and
               the acts that move a lesson through its states, each written as a new row.
- writer.py    the review-proposed-lessons workflow: the lesson review writer's verified summary of each
               item's evidence and the current lessons it may repeat.
- cross_check.py  the quarterly job that sends a sample of decisions to another region.
"""
