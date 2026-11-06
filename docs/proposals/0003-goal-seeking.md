# Proposal 3: Goal seeking for a package

**From:** ProcIntel, `src/procintel/prediction/goal.py` (Surya Yadav, October to November 2026)
**Status:** proposed, November 6, 2026

## The idea, as ProcIntel built it

A person names the outcome they want for a package, "awarded within N days", and ProcIntel shows the set-ups that reached it most often in the past. The fixed inputs stay fixed (country, sector, what is bought); the choosable ones are tried: the procurement method, among those the data holds for this kind of purchase, and, when a value is given, one to four equal lots. Each set-up is scored on the same history the model trains on: the share of comparable packages awarded within the target, with the count and the scope, narrowed to lots of similar value and to the country's region only when each keeps enough packages. Below the minimum count the answer is "not enough evidence". Two guards sit on every answer: a lot value outside the range a method was used for in the data gets "check the thresholds", and the result is association, not cause: packages set up this way were faster, which does not show that changing the set-up makes a given package faster.

## How it would work in Prism

Prism already answers "how long did packages like this take" with `find_comparables` and `estimate_time`, with a reference class of at least 20 and a first-person sentence when it holds back. Goal seeking asks the same question for each set-up a person could choose, and ranks the answers.

- **The question.** "Which set-ups reached a signed contract within N days most often?" The end event is the signed contract, as everywhere in Prism.
- **The set-ups.** Each selection method the Procurement Regulations allow for the package's category, as STEP names them, and one to four lots of equal value. Each set-up is one `find_comparables` call; the share within N days, the count and the reference class come back as summary fields, so the verifier can check every number.
- **The review threshold guard.** Prism's PPSD rows compare the whole package's estimate against the prior review threshold, never a lot's. Goal seeking keeps that rule: a set-up whose lots fall below a threshold that the whole package is above is shown with the threshold and the sentence "the review type follows the package's estimate, not a lot's", and Prism never writes "splitting".
- **The honesty guard.** Every answer carries ProcIntel's caveat in Prism's words: "Packages set up this way were signed sooner in the past. That does not show that changing this package's set-up makes it sooner; smaller and simpler contracts tend to use the faster methods."
- **Fewer than 20.** The set-up is listed with its count and no share.

## What changes from ProcIntel

The scoring history is Prism's contract awards and plans; the comparables rule is Prism's (the same category, method and value band, then the country and the region); the method list comes from Prism's method registry; the thresholds come from `config/thresholds.toml`.

## Open questions

1. Is goal seeking a tool the agent may call from a question, or only a page?
2. Does a set-up with lots show the whole package's review type, or each lot's?
3. Does the result go into a draft of planned dates, or stay a reading?
