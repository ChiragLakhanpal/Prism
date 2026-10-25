"""The retrieval loop (ticket 32; docs/PLAN.md sections 10 and 11, "Feedback").

- kinds: the kind of question a question is, from config/retrieval.toml, which a passage report and a
  ranking-lower decision are about.
- labels: the labeled set retrieval is measured on, in strata.ops.retrieval_labels: silver labels read from
  the ICR Reviews' "ICR para N" citations and the PADs' lessons sections, the judged notice queries, and the
  labels passage reviewers accepted from feedback, which no evaluation set ever takes.
- reports: passage reports from the evidence drawer (candidate labels), their groups, the passage
  reviewers' decisions, the scale rules, and the loop's measures.
- demotion: the passages a decision ranks lower for a kind of question, which search_passages moves below
  the others and never hides.
- judging: the queries written from award notices, their pools, the two query judges' grades and their
  agreement.
- weekly: the weekly retrieval run that builds the labeled set, applies the scale rules and measures the
  loop (bundle/retrieval.yml).

The replay harness's retrieval evaluation and the tuning gate are in strata.estimates.retrieval.
"""
