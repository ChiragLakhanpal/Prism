# Proposal 2: A timeline across a project's packages

**From:** ProcIntel, `web/src/lib/plan.ts` (Surya Yadav, October to November 2026)
**Status:** proposed, November 6, 2026

## The idea, as ProcIntel built it

A project is planned as a set of packages, each with a procurement type, a method, a value, an earliest tender date and, where it matters, the package it must wait for (`after`). ProcIntel's assessment gives each package a typical time to award and a slow case (p50 and p90, from the model where it beats the historical median, else from the median, with the number of comparable packages and the scope). `schedule()` lays the packages on one calendar: each starts at its earliest date or when the package it waits for is awarded, and the plan ends with a typical end, a slow-case end, the bottleneck package, and any chain that loops. `deadlineCheck()` names the packages that finish after a deadline in the typical case and the ones that only make it in the typical case. `resultsText()` writes the plan as sentences.

## How it would work in Prism

Prism checks a Procurement Plan row by row and gives each package a past range and, when the model beats its baseline, a time estimate from at least 20 comparable packages. The timeline puts those rows on one calendar for the whole plan.

- **Rows in.** The plan's activities as Prism already reads them (`check_plan`), with STEP's planned dates and the dependencies a person adds on the page ("waits for").
- **Each row's time.** `find_comparables` and `estimate_time`, as today: the past range's middle half and its slow end, or the estimate when it exists, each with its reference class and count, and the first-person sentence when Prism holds back from fewer than 20 comparables.
- **The calendar.** The end event is the signed contract, as everywhere in Prism, never a notice. The chart shows each package from its planned start to its typical and slow-case signing, the chain it waits for, the plan's typical and slow-case end, and the one package that sets the end. A loop in the chain is named, not drawn.
- **Against the closing date.** The packages whose slow case ends after the project's closing date are listed with their STEP references, as a reason to look, with the dates that back it.
- **Words.** The plan's dates are the plan's, never promises; "the slow case ends after the closing date", never "at risk".

## What changes from ProcIntel

ProcIntel schedules from tender notice to award; Prism measures to the signed contract, so the past ranges are longer and the plan's end is later. ProcIntel computes the schedule in the browser; Prism makes it a tool (`schedule_plan`), so the dates it prints are tool columns the verifier can check and the agent can cite.

## Open questions

1. Where do the dependencies live: on the page only, or saved with the draft of planned dates?
2. Is the chart a lane on the project's Timeline tab, or its own view on the plan check?
3. Does the public view see the calendar for active projects, or only closed ones?
