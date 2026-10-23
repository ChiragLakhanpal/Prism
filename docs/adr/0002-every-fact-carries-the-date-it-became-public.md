# Every fact carries the date it became public, so Strata can answer as of any past date

Every record, passage and assertion stores the date it became public, and ratings also store the period they describe. Every query and retrieval can then be limited to what was public on a chosen date. This lets Strata answer any question as it would have on a past date. The hindsight test depends on that: freeze Strata at a closed project's approval date and check whether it would have flagged the risks the completion report later blamed. The test doubles as Module 4's recall measure, and the same filter keeps the predictive models free of leakage.

## Consequences

- Every table carries a public-from date, and every retrieval and tool takes an optional as-of date. Adding this later would mean touching every table and every tool.
- Sources that revise past values in place (governance indicators, re-issued reports) need each version kept, not overwritten.
