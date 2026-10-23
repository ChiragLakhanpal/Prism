# Strata: build spec

Status: ready-for-agent. Drafted October 22, 2026 from the agreed plan. Read it with docs/PLAN.md (most authoritative for scope, platform, data, formats and phases), docs/blueprint/strata-blueprint.html (the nine wireframes and the reasoning behind them), GLOSSARY.md (every term here is used as defined there), DESIGN.md (every screen, slide and figure), docs/adr/0001 to 0004 and docs/assessment.md. The tickets that build this spec sit in the issues folder beside this file, numbered in dependency order.

## Seams

Behaviour is tested at five seams and nowhere else. Each seam has an offline adapter, which the pre-commit gate uses, and a live adapter, which the full gate, the benchmark, the release gate or the demo-ready command uses. Two adapters per seam make each one real rather than hypothetical. All five share one fixture: recorded source pages and documents for the demo plan (the Northern Water Works Development Agency's October 9, 2026 plan for P156634), the showcase project (P130164) and a handful of comparable packages, built into a small DuckDB database by the lakehouse run itself, so the fixture can never drift from the code that makes the real tables.

1. **The lakehouse run, over a fixture.** Recorded API pages and document files go in; the run order (bronze, then silver, then gold, then the data readiness measures in strata.ops) comes out as tables. Tests assert keys and joins, a public date on every row, passages with their paragraph and page numbers, supplier matches, edges, assertions, disagreements, proposed lessons whose quotes were found on the cited page, contact details stripped, and every data readiness measure as a count with its denominator. Offline adapter: DuckDB. Live adapter: the bundle's job in the workspace, run over the same fixture as a smoke test. Catches wrong joins, lost dates, leaked contact details and unread pages. Misses scale and quota behaviour, which the nightly job's run records show.

2. **The tool contract.** Every tool in the registry is called by name with its arguments, an optional as-of date and the viewer's view. It returns rows or passages, each with a stable evidence id, its public date and the fields of its source line, plus a coverage line (how many matched, how many were used, and why the rest were not) and, where the rules require it, an abstention with its reason. The ground-truth SQL from fairshare's gate lives here. Offline adapter: the fixture database and a fixture search index. Live adapter: the SQL warehouse, Genie and AI Search, called with the viewer's own token. Catches wrong rows, rows that became public after the as-of date, a range built on fewer than 20 comparables, and a view that sees more than its rules allow. Misses whether the agent picks the right tool.

3. **The answer contract: HTTP routes and the event stream.** A question, a package or a draft request goes in over HTTP. The stream returns steps, the answer as sentences with evidence ids, the counts behind the check line, removed sentences with their reasons, disagreements and the run's trace ids. Draft states, exports, feedback, follows and uploads are driven through the same routes. Offline adapter: a scripted agent that replays recorded model outputs (tool calls, then claims as JSON), with the tools running on the fixture. Live adapter: the Foundry agent with the live tools, used by the benchmark, the must-refuse set, Foundry evaluations and the smoke question. Catches a number with no row behind it, a citation that did not come back this turn, a quote that is not on its page, advice with no lesson or comparable, a one-sided disagreement, a missed refusal, a preview that can check or export, and an upload seen outside its team. Misses layout and wording on screen.

4. **The screens.** Playwright drives the built app against a mocked API that serves responses recorded from seams 2 and 3, so screen tests and contract tests share their fixtures. Tests assert the behaviour each wireframe names (what a click opens, what Escape closes, where focus returns, what a preview disables), accessibility (axe at WCAG 2.2 AA, keyboard paths, reflow at 320px), copy drawn only from the copy file, and that nothing links to /present. Catches broken flows and accessibility regressions. Misses whether the data behind a screen are right; seams 1 to 3 own that.

5. **The replay harness.** Given a cutoff date and a scorer, it freezes Strata at that date (ADR 0002), runs, and scores the result against what became public later. It has three adapters: model backtests (the time estimate, delay per STEP step, rebidding risk, and the early-warning hazard model against the fixed signals), retrieval evaluation (recall at 20, precision at 10 and nDCG at 10, using only documents public before each query's date) and the hindsight test (Strata's top five risks per package against the risks completion reports later blamed). Results go to strata.ops and MLflow, and every number in the proposal comes from here or from seam 1's measures. Offline adapter: a tiny fixture run that proves the harness filters by date and computes each score from inputs whose answers are known. Live adapter: the full pilot slice. Catches leakage, ranges that are too narrow or too wide, and a challenger that loses. Misses how people behave after seeing Strata's numbers, which the exposure logs measure.

What is not a seam: the parts inside a module (the page router's rules, each of the verifier's six checks, the survival model's features, the box's intent rules) are tested only through these five. A helper that seems to need its own test belongs behind one of them.

The gates use the seams as follows. The offline gate, run before every commit, runs seam 1 over the fixture, seam 2's tool tests and ground-truth SQL, seam 3 with the scripted agent, seam 4's screen tests and seam 5's fixture run, with the network off, in under two minutes. If the screen tests threaten that budget they run in parallel workers; they never leave the gate. The full gate adds seam 3 with the live agent (the benchmark, the must-refuse set and Foundry evaluations) and the Genie benchmark. The release gate is the hindsight test on seam 5's live adapter.

## Problem Statement

A World Bank procurement specialist reviewing a borrower's draft Procurement Plan has to judge, package by package, whether the dates are realistic, whether the selection method and market approach fit, and which risks belong in the borrower's PPSD. The evidence exists, but it sits in three places that do not talk to each other: records of what happened (contract awards, notices, project data, disbursements, governance indicators), operational documents on how it was done (Procurement Plans in STEP, ISRs) and evaluations that explain why it worked or not (PADs, ICRs, ICR Reviews and PPARs). Linking them is manual. The World Bank's own study of procurement delays did it through "extensive manual review" of aide-memoires, plans and completion reports, and found that about 22% of 656 works contracts in STEP were signed on their planned date while 28% were signed more than 270 days late. IEG found the PPSD is "typically a generic document with similar content across many projects".

The same gap hits everyone around the plan. An implementing agency's procurement officer (a PIU, PMU or PCU locally), often working in French, Spanish or Portuguese, drafts the PPSD and sets a planned date for every STEP step without seeing how comparable packages in their own or neighbouring countries went. A task team leader preparing a mission rebuilds the project's procurement picture from scratch each time. A member of the public who reads about a large award or a late road cannot follow the contract from notice to award to plan dates to ISR to completion report. Lessons written into completion reports rarely reach the next plan, and when reports disagree about how a project went, nobody shows both sides.

Any tool that helps here carries two extra burdens. It must never invent a number or a quote, because a specialist who repeats a wrong figure to a borrower loses credibility. And it must respect who decides: the borrower prepares the PPSD and the Procurement Plan; the World Bank's specialist supports the borrower, assesses the implementing agency's procurement risk and clears the plan. Nothing a tool produces may look like a World Bank review, clearance or no-objection.

Finally, the people who will judge Strata, a World Bank data and AI panel, score it on a 100-point rubric across four modules and will ask for live code changes in the second round. A platform that cannot show where each number came from, or cannot change in minutes, fails them too.

## Solution

Strata is procurement intelligence on World Bank open data, deployed as a Databricks App that acts as each viewer. It links the three strata (What, How and Why) once, keeps them current nightly, and shows its work: every claim is cited to a record or to a passage (a numbered paragraph or table row, with its page), and every answer passes six checks before anyone sees it.

- **Check a plan** is the lead entry. Strata checks every package in a published Procurement Plan (or, for an implementing agency, a private upload of a STEP export) against past ranges, the review thresholds and the plan's own dates, measures delay from the first published planned date, marks only the exceptions (Needs a look, Watch, Data note), says what it cannot see, and drafts review notes on the rows that matter.
- **Plan a package from a sentence** serves concept stage. One sentence becomes editable criteria, with review type and market approach computed from the thresholds. The package workspace then shows the past range of comparable packages as dots (open packages hollow and counted), Strata's time estimate in a second lane on the same month axis with its track record, the borrower's plan as a draggable line with a count readout, a planned date for each STEP step, procurement risks and what helped (lessons quoted to the paragraph and page), approach options with fair what-ifs, rebidding risk labeled experimental, and an optional check of qualification criteria and the cost estimate.
- **Drafts** look like what they will become: suggested risk rows in the PPSD template's own columns (Short Form unless a contract crosses the guidance's Table I thresholds), review notes, the procurement summary for the Project Paper, a mission brief, and for implementing agencies a planned date for every STEP step and a STEP row. Strata writes descriptions and mitigations with counts and sources as footnotes and leaves risk owners, ratings, references and actual dates to people and STEP. Only a person moves a draft from Draft to Checked by you to Exported, and exporting sends nothing.
- **Projects** are the hub. Every P-code links to a project page with Summary, Procurement, Timeline (What, How and Why on one time axis, with disagreements marked), Documents and Connections (a one-hop neighbourhood of about 20 nodes at most). An activity page traces a contract from plan row to notice to bids to contract to the passages that appeared together with it. World Bank staff follow projects and see signals with their reasons and track record, never a score.
- **Lessons** come from ICRs, ICR Reviews and PPARs, enter only when their quote is found word for word on the cited page, and are decided by people (an accredited procurement specialist recommends, a lead procurement specialist decides). Each lesson has versions; drafts cite a lesson at a version and show was and now when it changes.
- **Disagreements** between reports stay on screen with both sides in the order they were written, the source Strata leans on, the rule that decided it, and what changes if you keep the other.
- **Data readiness** is a page users can read and a dashboard page for the data team: coverage, links, how well documents were read, and freshness, with gaps such as the missing FY2017–19 contract records stated rather than hidden.
- **The view switch** previews honestly what an implementing agency officer or the public would see, and an as-of date replays any page as it would have looked on a past date.
- **Behind it:** Unity Catalog tables as the knowledge graph, numbered-paragraph passages in a hybrid AI Search index, Genie over metric views, survival models with calibrated ranges and rolling backtests, a Foundry agent whose tools run in the app as the viewer, a deterministic verifier, three loops sharing one dated store, a hindsight test as a release gate, cost caps, and one AI/BI dashboard.
- **For the panel:** a proposal written by module, every number linked to a measured result; a deck at /present that nothing in the app links to; a demo-ready command; and about ten change drills rehearsed to land in under ten minutes each with the gate green.

## User Stories

### World Bank procurement specialist: planning and strategy

1. As a World Bank procurement specialist, I want to check a borrower's latest published Procurement Plan package by package, so that I know which packages need a look before I advise the borrower.
2. As a World Bank procurement specialist, I want every package shown with its STEP activity reference, so that I can find the same activity in STEP without guessing.
3. As a World Bank procurement specialist, I want delay measured from the first published planned date, so that plan updates that re-date steps do not hide how late a step really is.
4. As a World Bank procurement specialist, I want only the exceptions marked (Needs a look, Watch, Data note) and packages with no signals folded away with a count, so that I can spend my time on the few rows that matter.
5. As a World Bank procurement specialist, I want each mark to state its reason in one past-tense sentence with dates and amounts, so that I can repeat it to the borrower without rechecking.
6. As a World Bank procurement specialist, I want Strata to read the selection method from the plan's Method column rather than from the reference, and to say so when they differ, so that a mislabeled reference does not mislead the check.
7. As a World Bank procurement specialist, I want data notes shown in the row they concern, such as a signed contract whose Actual Amount reads 0.00, so that I know where the record is weak.
8. As a World Bank procurement specialist, I want the page to say what Strata cannot see (the prior-review queue, complaints, contract amendments and contract management reports), so that I never mistake silence for a clean record.
9. As a World Bank procurement specialist, I want to see what changed since the last version of a plan, so that I review only what is new.
10. As a World Bank procurement specialist, I want to draft review notes on the rows that matter in one action, so that my advice starts from the evidence.
11. As a World Bank procurement specialist, I want the past range of comparable packages for a package the borrower is planning, so that I can tell whether its planned procurement cycle time is realistic.
12. As a World Bank procurement specialist, I want the comparables chosen by stated criteria (method, category, market approach, review type, size band, region and period) that I can change, so that I can defend the reference class.
13. As a World Bank procurement specialist, I want each comparable drawn as a dot I can open, with packages still open drawn hollow and counted, so that the range does not look shorter than it was.
14. As a World Bank procurement specialist, I want the borrower's plan drawn as a line through the chart with a count readout such as "4 of 40 signed within 6 months", so that I can discuss the plan in plain numbers.
15. As a World Bank procurement specialist, I want to drag the plan line or type a number, by mouse or keyboard, so that I can try other dates.
16. As a World Bank procurement specialist, I want Strata's time estimate for this specific package beside the past range, with a sentence saying why the two lanes differ, so that I can see how this package differs from its comparables.
17. As a World Bank procurement specialist, I want a track record under every time estimate, stated as how many unseen packages finished inside its 8-in-10 range, so that I can judge how far to trust it.
18. As a World Bank procurement specialist, I want Strata to say "I'm not giving a range" and list every comparable when fewer than 20 match, subgroups included, so that I am never shown a range built on too few cases.
19. As a World Bank procurement specialist, I want to compare market approach, prequalification and lotting options with counts of how comparable packages went, worded as "went with" and never "caused", so that I can discuss procurement approach options honestly.
20. As a World Bank procurement specialist, I want review type and market approach computed from the thresholds and labeled as computed, so that I do not have to look them up and can see how they were set.
21. As a World Bank procurement specialist, I want a planned date for each STEP step, with the step that ran longest among comparables named, so that the plan's step dates are realistic.
22. As a World Bank procurement specialist, I want rebidding risk shown as a count of comparable packages that were advertised again, with the reasons quoted from award notices and an "experimental" label, so that I give it the weight it deserves.
23. As a World Bank procurement specialist, I want the procurement risks that came up again and again for comparable packages, each with what helped and the report that says so, so that the borrower's PPSD stops being generic.
24. As a World Bank procurement specialist, I want suggested risk rows for the borrower's PPSD in the template's own columns with sources as footnotes, so that the borrower can paste them straight in.
25. As a World Bank procurement specialist, I want the Long Form columns offered only when a contract crosses the PPSD guidance's Table I thresholds, so that the draft follows the guidance.
26. As a World Bank procurement specialist, I want the implementing agency's own track record (how its past packages went against its plans), so that I can assess its procurement risk.
27. As a World Bank procurement specialist, I want a procurement summary for the Project Paper drafted from the plan check and the PPSD evidence, so that I spend my time checking rather than writing.
28. As a World Bank procurement specialist, I want a final plan check saved as the baseline after negotiations, so that later delay is measured against the plan that became binding.

### World Bank procurement specialist: tender design and packaging

29. As a World Bank procurement specialist, I want to paste a package's qualification criteria and compare them with comparable packages whose criteria are public, so that I can check that the market can meet them before advertisement.
30. As a World Bank procurement specialist, I want to see how often bids for comparable packages were rejected and the rejection reasons quoted from award notices, so that I can spot criteria that shut bidders out.
31. As a World Bank procurement specialist, I want the cost estimate compared with signed amounts of comparable packages, so that I can catch a cost estimate set below market rates before it forces rebidding.
32. As a World Bank procurement specialist, I want lessons on cost estimates and specifications surfaced beside the criteria check, so that past fixes inform the bidding document.
33. As a World Bank procurement specialist, I want old method names (ICB, NCB, Shopping, Direct Contracting) accepted when I type them and the current Regulations' names written back, so that I can work the way I am used to without Strata repeating outdated terms.

### Task team leader: execution and monitoring

34. As a task team leader, I want to follow the projects I lead, so that the ones with signals reach me without searching.
35. As a task team leader, I want each followed project's status first (Needs a look, Watch, No signals) with the signals that put it there, one line each, past tense, with counts, so that I can see why at a glance.
36. As a task team leader, I want the status definition on the column header, so that I know "Needs a look" means three signals or one strong one and that a signal is a reason to look, not a finding.
37. As a task team leader, I want each signal's track record shown, so that I can calibrate how much a signal usually means.
38. As a task team leader, I want projects with no signals folded away with a count, so that the list stays short.
39. As a task team leader, I want to add a project to a mission brief in one action, so that preparing the mission starts from the signals.
40. As a task team leader, I want a mission brief with the latest plan per implementing agency, awards since the last ISR, the rating history, disbursement and a closing check, so that I arrive at the mission prepared.
41. As a task team leader, I want packages whose planned completion passed with no signed contract shown with how many days remain before the project closes, so that I can decide on support or restructuring in time.
42. As a task team leader, I want actual amounts far above their estimates and late direct-selection activities shown as signals, so that I can ask about them early.
43. As a task team leader, I want closing-date extensions and restructurings counted from the loan history, so that I can see a project's pattern, not one snapshot.

### Implementing agency procurement officer

44. As an implementing agency procurement officer, I want to check my plan before I submit it, on a private upload of my STEP export or on the latest published version, so that problems are caught before the World Bank sees them.
45. As an implementing agency procurement officer, I want my upload kept with my team and never shown to anyone else, so that my Official Use Only draft stays private.
46. As an implementing agency procurement officer, I want a planned date for every STEP step of a package, with the comparables behind it, so that my plan's dates are realistic.
47. As an implementing agency procurement officer, I want suggested PPSD risk rows with their sources, so that my PPSD reflects what happened to comparable packages.
48. As an implementing agency procurement officer, I want comparable packages from my own and neighbouring countries, so that the evidence matches my market.
49. As an implementing agency procurement officer, I want sources in French, Spanish and Portuguese searchable and quoted in their own language, so that reports written in my language count as evidence.
50. As an implementing agency procurement officer, I want answers and drafts in my working language on request, with quotes kept in their original wording, so that I can use them directly.
51. As an implementing agency procurement officer, I want a STEP row exported in STEP's own columns with planned dates filled and everything else left to me and STEP, so that nothing I did not decide ends up in my plan.
52. As an implementing agency procurement officer, I want help with an activity that has to be advertised again, with what helped comparable packages, so that the second attempt goes better.
53. As an implementing agency procurement officer, I want signals measured against my own plan for my agency's projects, so that I see my delays before my task team does.

### The public

54. As a member of the public, I want to search for a project and open its contract trail from notice to award to plan dates to ISR to completion report, so that I can follow where the money went.
55. As a member of the public, I want neutral words with no signals, time estimates or disagreements on active projects, so that what I read does not prejudge a live process.
56. As a member of the public, I want every claim to link to the public document it came from, so that I can check it myself.
57. As a member of the public, I want the lessons library, so that I can see what the World Bank's evaluations found about procurement.
58. As a member of the public, I want to know that Strata is an independent demo and not a World Bank product, so that I do not mistake it for an official source.
59. As a member of the public, I want individuals' names and notice contact details never shown, so that private people are not exposed.

### Anyone answering a question

60. As any user, I want one box on every page that tells me what Enter will do before I press it (open a project, check a plan, plan a package, or ask), so that a question never silently becomes a package.
61. As any user, I want a pasted P-code, STEP reference or loan number in any of its four forms to take me straight to the right page, so that I never have to reformat what I copied.
62. As any user, I want the answer to open with "In short", so that I get the conclusion before the detail.
63. As any user, I want every claim one hover from its source, with the matching words highlighted, so that I can check a claim without losing my place.
64. As any user, I want a click on a citation to open the whole numbered paragraph beside the answer, with a link to open the document at its page, so that I can read the passage in full.
65. As any user, I want a neutral check line that says what was checked and what was not, so that I neither over-trust nor dismiss the answer.
66. As any user, I want the first sentence the checks removed shown under the answer with its reason, so that I can see the checks working.
67. As any user, I want steps announced while the answer is being built, so that I know Strata is working and on what.
68. As any user, I want Strata to refuse in the first person when I ask for something it does not do (supplier scores, fraud inferences, comments on live tenders), so that I know why and what it can do instead.
69. As any user, I want every count to name its reference class and denominator, and no percentage from fewer than 20 cases, so that small numbers are not dressed up.
70. As any user, I want a coverage line under any number that depends on linked records, such as "Based on 37 of 52 matching packages; 15 lacked the STEP reference that links notice to contract", linking to the sources behind it on the Data readiness page, so that I know how complete the evidence is.
71. As any user, I want to see a page as it would have looked on a past date, so that I can check what was known when.
72. As any user, I want the app to work on a small screen and a slow connection, so that I can use it in the field.
73. As any user who relies on a keyboard or a screen reader, I want every chart, drawer and table reachable and named, so that I can use Strata fully.

### Anyone reading evidence that disagrees

74. As any user, I want two reports that disagree shown side by side in the order they were written, with equal weight, so that I can judge them myself.
75. As any user, I want the source Strata leans on tagged, with the rule in one sentence and a line on what changes if I keep the other, so that I understand and can override the choice.
76. As any user, I want to keep the other source, with a reason that goes into the evidence pack, so that my judgment is recorded.
77. As any user, I want a warning only when a disagreement changes a number or claim in my answer or draft, and a quiet note otherwise, so that constant warnings do not train me to ignore them.
78. As any user, I want a rating that moves over time shown as a trajectory, not a disagreement, so that normal change is not mistaken for disagreement.
79. As any user, I want a project's timeline with What, How and Why in three lanes on one time axis, so that I can see what was known when.

### Drafts and exports

80. As any author of a draft, I want it to move from Draft to Checked by you to Exported only when I move it, so that nothing leaves without a person.
81. As any author of a draft, I want the draft bar to say what exporting does and what it is not, so that no export can be mistaken for a World Bank review, clearance or no-objection.
82. As any author of a draft, I want the bar to say how many of its sources I opened, saved with the evidence pack, so that how I checked is recorded.
83. As any author of a draft, I want to export to Word in the template's columns with footnotes, a STEP row as CSV, and an evidence pack as PDF and CSV, so that I can use the work where it belongs.
84. As any author of a draft, I want Discard set apart from the other actions and undoable, so that I cannot lose work by accident.
85. As any author of a draft, I want the export to end on a clear success that says what was saved, so that I know it worked.
86. As any author of a draft, I want a draft that cites a lesson to show was and now when that lesson changes, with "Update this row" or "Keep version 1, with a reason", so that nothing in my draft changes without me.
87. As any author of a draft, I want export blocked only when a cited lesson version was retired as wrong, so that I am stopped only when it matters.
88. As any author of a draft, I want short counts of what is left ("2 of 3 risk owners set"), so that I can see how close the draft is to done.

### Continuous learning: lessons and their reviewers

89. As an accredited procurement specialist, I want proposed lessons in a queue only reviewers see, each with its verbatim quote and page, so that I can recommend or reject it on the evidence.
90. As an accredited procurement specialist, I want to give a reason for every recommendation, so that the decision is accountable.
91. As a lead procurement specialist, I want to decide on a recommended lesson within 10 business days, with a second person always involved, so that the library stays trustworthy and current.
92. As a lead procurement specialist, I want to be kept off decisions about my own projects, so that recusal is enforced rather than remembered.
93. As a lead procurement specialist, I want to merge a proposed lesson into an existing one as further evidence, re-check a lesson, or retire it, with the reason kept, so that the library improves without losing history.
94. As a lead procurement specialist, I want a quarterly 10% cross-check of decisions by another region, so that regions do not drift apart.
95. As a lead procurement specialist, I want lessons that rest on an ICR alone marked "Awaiting IEG review", and an ICR Review's restatement added as IEG-endorsed evidence, so that independence shows in the evidence.
96. As any World Bank staff member, I want the Lessons page to open on lessons that changed where I used them, then what is new, then my feedback, then the library, so that what affects my work comes first.
97. As any World Bank staff member, I want to filter the library by stage, method, sector and status, so that I can find lessons for the package in front of me.
98. As any user, I want lessons ranked by fit and evidence, never by how often they were used, so that popular lessons do not crowd out better ones.
99. As any user, I want to mark a passage as "Wrong passage" or "Not useful", so that retrieval improves.
100. As any user, I want to be told what my feedback fixed ("You marked 2 passages as wrong; 1 is fixed, and 14 answers now cite the right paragraph"), so that I know it mattered.

### Search, model and loop owners

101. As the search owner, I want feedback to become candidate labels that specialists review weekly, never production data, so that one person's mistake cannot change what everyone sees.
102. As the search owner, I want tuned search to ship only when it loses nothing on the held-out set or the hindsight set, so that tuning never makes retrieval worse.
103. As the model owner, I want rolling backtests that train before a date and test on the next 12 months, for 2021 to 2025, so that I know how the time estimate performs on packages it had not seen.
104. As the model owner, I want a challenger promoted only after it wins the backtest and a quarter in shadow, co-signed by the lead, so that changes are earned.
105. As the model owner, I want retraining triggered when interval coverage leaves 75–85% for two months, error trails the past range by more than 10%, the input mix drifts, or a new Regulations edition takes effect, so that drift is caught early.
106. As the model owner, I want every exposure logged (STEP reference, the range shown, the option chosen) and later plan rows within 14 days of Strata's value marked as anchored, so that I can tell Strata's influence from its accuracy.
107. As the model owner, I want models and lessons tagged with the Regulations edition each project follows, so that a new edition marks them for re-check.

### The data team

108. As a member of the data team, I want every source fetched by watermark and only what changed parsed and embedded, so that the nightly job stays within Free Edition's daily quota.
109. As a member of the data team, I want every row to keep the date it became public, so that as-of answers and leakage-free models are possible.
110. As a member of the data team, I want bronze and silver rebuilt from source and never edited by hand, so that every table can be reproduced.
111. As a member of the data team, I want documents routed by page (the published text for clean pages, the layout parser for scans and tables), so that each page is read at the lowest cost that reads it well.
112. As a member of the data team, I want a numbered paragraph to be the citation unit, with its section path, paragraph number, PDF page, printed page, language and parse route, so that every citation points to something a person can find.
113. As a member of the data team, I want a table read into typed rows plus one summary passage that never backs a number, so that numbers always come from rows.
114. As a member of the data team, I want suppliers matched on STEP supplier IDs first, names only where no ID exists, and uncertain matches sent to a person, so that no supplier is merged wrongly.
115. As a member of the data team, I want a joint venture kept as its own supplier linked to its members, and "INDIVIDUAL CONSULTANT" never shown by name, so that suppliers are counted right and individuals stay private.
116. As a member of the data team, I want contract-to-passage links scored on project, sector, time, text similarity and shared mentions, and shown as "appeared together", so that links are useful without claiming cause.
117. As a member of the data team, I want contact names, emails and phone numbers stripped at ingestion, with the count recorded, so that personal data never enters the store.
118. As a member of the data team, I want data readiness measured at every step (coverage by year, pages per route, read well, linked to a project, lessons verified, freshness), so that gaps are visible and ranked by what fixing them would unlock.
119. As a member of the data team, I want a stress shelf of hard documents with a recorded outcome for each, so that I know where reading fails.
120. As a member of the data team, I want quality checks recorded per pipeline run and lineage from source to answer, so that I can prove where any number came from.
121. As a member of the data team, I want Azure spend shown against the budget, with hard caps in place, so that the free credit is never overrun.
122. As a member of the data team, I want the FY2017–19 gap filled from award notices in local currency and labeled as such, so that missing years are handled honestly.
123. As a member of the data team, I want loan numbers normalized from their four forms once, so that every join on a loan works.
124. As a member of the data team, I want governance indicators kept as each version was published and lagged to what was public at the time, so that no model sees a revised value early.

### The reviewing panel and the presenter

125. As a member of the reviewing panel, I want to land as World Bank staff on a Home with seeded examples labeled as examples and a Start here strip with one example per stage, so that I can see every stage in the first minute.
126. As a member of the reviewing panel, I want to open the Data readiness page, the lineage and the stress-shelf documents, so that I can judge the ingestion and knowledge architecture (Module 1).
127. As a member of the reviewing panel, I want to open the model card, the backtest results and the track records, so that I can judge the time estimates and how they were made (Module 2).
128. As a member of the reviewing panel, I want to see the removed-sentence box, the check line, the benchmark results and the Foundry evaluations, so that I can judge faithfulness and attribution (Module 3).
129. As a member of the reviewing panel, I want to see disagreements resolved by a stated rule with both sides shown, so that I can judge how disagreeing evidence is handled (Module 3).
130. As a member of the reviewing panel, I want to see the three loops with their gates, owners and indicators, the KPIs and the phased rollout, so that I can judge continuous learning and the implementation strategy (Module 4).
131. As a member of the reviewing panel, I want the hindsight test reported as "caught X of Y blamed risks across N projects (95% interval), at five per package" beside a checklist baseline, so that I can judge recall honestly.
132. As a member of the reviewing panel, I want the proposal written by module with every number linked to a measured result and a rubric map, so that I can score each dimension.
133. As a member of the reviewing panel, I want the deck at /present, findable from the proposal and the README, so that I can follow the story without the app carrying demo scaffolding.
134. As a member of the reviewing panel, I want to request a live change (a data source, a tool, a signal threshold, a country, the model, the evidence ladder, a package form field, copy, a benchmark question, a dashboard tile) and see it land in under ten minutes with the gate green, so that I can judge changeability.
135. As the presenter, I want one demo-ready command that restarts the app, warms the warehouse and Genie, asks one smoke question and rechecks the P156634 signals, so that the demo starts warm and current.
136. As the presenter, I want anything unfinished labeled "designed, not built", so that the demo never overclaims.

## Implementation Decisions

### Platform, identity and limits

- Databricks Free Edition holds the lakehouse, the knowledge model, search, Genie, the models, the app and the dashboard (ADR 0001). Strata shares fairshare's workspace but has its own catalog, strata, with its own medallion schemas, pipelines and nightly job.
- Microsoft Foundry project Strata, on wb-strata in resource group WorldBank-demo, holds the agent, guardrails, evaluations and agent traces. Azure OpenAI deployments: gpt-5.4-mini for the agent, gpt-5.4 for drafting, hard questions and the entailment judge, gpt-5.4-nano on Global Batch for bulk extraction, and text-embedding-3-large at 1,024 dimensions. There is no fallback model.
- The agent decides and the app runs its tools with the viewer's own token (ADR 0003), so the app holds every row and passage an answer relies on and each viewer sees only what their permissions allow. Multi-step jobs are Microsoft Agent Framework workflows in code; Foundry portal workflows are not used (they retire on December 1, 2026).
- Shared workspace limits shape the design: three apps (one each for Strata and fairshare), one AI Search endpoint (Strata's), one 2X-Small SQL warehouse, five concurrent job tasks and one daily compute quota. Apps stop 24 hours after each start or deploy. The two nightly jobs run at different hours.
- Azure spend is held by hard caps, because budgets only notify: a tokens-per-minute limit on every deployment, a daily page cap in ingestion, at most two replicas for anything hosted, and paid resources deleted after the pilot. The subscription moves to pay-as-you-go before the free credit ends on November 10, 2026.
- Gap fills are built only if a day-one test shows the gap: a Container Apps job for ingestion (test 1), Content Understanding prebuilt-layout for parsing (test 3), and a Container Apps copy of the app behind Entra sign-in for reviewers (test 6). A day-one results document in the repo records each test's result and the path chosen, and every ticket that touches one of these reads it.

### Repository and what comes from fairshare

- A new private GitHub repo, strata, with the reviewers as collaborators. Code from fairshare is copied, never imported, following PLAN.md section 12's three lists (as is, adapt, leave).
- The repo holds, as separate modules: the lakehouse (sources, transforms, data readiness), the document reader, the knowledge model, the tool registry and its tools, the agent (instructions, sync, the answer loop, the verifier, workflows), the estimates (comparables, models, the replay harness), the app server, the web app, the dashboard definition, the bundle, the benchmark and evaluation sets, the gates, the demo-ready command, the proposal and the deck.
- fairshare's rules in CLAUDE.md, its pre-commit hook and its destructive-command hook come over as they are, adapted only where Strata's names differ.

### Ten single places, for the change drill

Each change in PLAN.md section 15 lives in exactly one place, so each lands in under ten minutes:

1. **The source registry**: per source, its endpoint and dataset and resource ids, watermark field, cadence, the dataset name and license line for attribution, and its silver transform. Adding a data source is one entry plus one transform.
2. **The tool registry**: per tool, its name, description, parameter schema, adapter and result shape. The agent's tool list and the tool section of its Foundry instructions are generated from it.
3. **The thresholds file**: every signal and plan-check threshold (planned completion passed, days before closing, actual-to-estimate ratio, late direct selection, closing-date moves, the "Needs a look" rule), the review thresholds that compute review type, the market approach thresholds per country, and the PPSD guidance's Table I thresholds.
4. **The slice file**: the countries, sectors and fiscal years of the document slice, the showcase project, the demo plan and the stress shelf.
5. **The model file**: the deployment used for each role (agent, drafting and judge, batch extraction, embeddings). Swapping a model is one line.
6. **The evidence ladder**: the ordered rules for outcome judgments, the rule for assertions about a moment, and the tie rules.
7. **The package form schema**: each criterion chip, its group (What, Where, How), its STEP field name, and whether it is typed, computed or guessed.
8. **The copy file**: every user-facing string, following DESIGN.md section 7.
9. **The benchmark file**: the four kinds of question (SQL, documents, estimates, refusals) with expected answers or citations, including the must-refuse set.
10. **The dashboard definition**: pages and tiles as code.

A roles file (which workspace groups are reviewers, leads and implementing agency teams) sits beside them.

### Data and the lakehouse run

- Sources are those in PLAN.md section 3: Finances One datasets DS00005 (awards since FY2020), DS01004 (awards FY2001–16, frozen), DS00053 (IEG ratings), DS00001 and DS00047 (loans and credits, latest) and DS00976 and DS00975 (monthly history, a slice only); the v3 search APIs for procurement notices, projects and documents (the v2 APIs are stale and the old Socrata API is gone); the Indicators API for CPIA (IQ.CPA codes, IDA countries only) and WGI (GOV_WGI codes); and the Procurement Regulations, 7th edition (September 2025), the PPSD Short and Long Form templates and guidance, and the Procurement Plan template in English and French.
- Scope: structured data for every country (under 0.5 GB); documents for the pilot slice (Kenya, Bangladesh, Vietnam and Pakistan, water and transport, approved FY2012–2025: 128 projects, about 43,000 pages before keeping only the latest plan per implementing agency); the showcase project P130164; the demo plan; and the stress shelf.
- Every source is fetched by watermark. Bronze keeps API pages as received with fetch time and source, and the bronze files volume keeps PDFs and text files. Silver holds typed, cleaned tables per source and parsed document elements (pages, sections, passages, table rows). Gold holds the knowledge model, metric views for Genie, and features and scores. strata.ops holds data readiness measures, pipeline runs, agent runs, packages, drafts and their states, follows, uploads, feedback and candidate labels, exposure logs, evaluation results, usage events and cost. Bronze and silver are rebuilt from source and never edited by hand.
- Transforms are plain SQL queries, one per silver or gold table, kept in one place and run unchanged on Databricks (wrapped as pipeline tables) and on DuckDB in the offline gate, with dialect differences handled by one transpile step. Python is used only where SQL cannot do the work (page routing, paragraph division, supplier matching, model calls, survival fitting), and those functions take and return plain rows so both engines can call them. This is what lets seam 1 build the fixture database the other seams use.
- Every row keeps the date it became public in its public_from column (ADR 0002): the date the source published it or, where that date is missing or in the future, the date Strata first fetched it. Assertions also keep the period they describe and the date they were made. Sources that revise past values in place (governance indicators, re-issued reports) keep every version.
- Joins: project_id at project level; the STEP reference joins a notice's bid_reference_no, an award's borrower_contract_reference_number and a plan's activity reference (about 64% of recent awards carry one); the STEP supplier ID in award notices equals the awards table's supplier_id; loan numbers are normalized once from their four forms (IDA60290, IDA-60290, 60290, IDA / 60300); country and year join CPIA and WGI, lagged to what had been published at the time. The method is read from a plan's Method column, never from the reference.
- Quirks are handled on purpose: fiscal years run July to June; mixed date formats are parsed to dates; the FY2017–19 gap is filled from award notices in local currency and labeled; a joint venture's rows (one per member, amount divided equally) become one joint-venture supplier linked to its members with the amount kept once at contract level; "INDIVIDUAL CONSULTANT" is never shown by name; currencies are kept with their units and converted only where a conversion is labeled; the two sector taxonomies map to one; duplicate ISR ratings from the projects API are removed and the rating history is read from ISR text; signed rows with an Actual Amount of 0.00 become data notes; contact names, emails and phone numbers in notices are stripped at ingestion and counted.
- First published planned dates come from the earliest plan version that lists each activity reference, found cheaply in the published text; only those versions, the latest version per implementing agency and the version before it (so changes between versions can be shown) go through the layout parser.

### The knowledge model

- The knowledge graph is Unity Catalog Delta tables with declared keys plus one edge table (ADR 0004): country, governance score, project, package (keyed by STEP reference), notice, contract, contract supplier, supplier, document, passage, lesson, lesson version, lesson evidence, risk factor (a closed list), assertion, disagreement and edge. Every row has a public date.
- An edge records a from id, a to id, its kind (borrows, plans, advertised in, awarded as, signed by, lists bidders, described in, has, source of, quoted by, tagged, appeared together), a score with its components (project, sector, time, text similarity, shared mentions) and a public date. A contract linked to a passage is always shown as "appeared together", never as cause. Paths are at most four hops, handled by joins and recursive SQL; whole-graph analysis would run as GraphFrames jobs and is not needed in the pilot.
- An assertion records its subject (project, package or contract), its attribute (a rating, a date or an amount, by kind), its value, the period it describes, when it was made, its public date, its source document and passage, and its evidence tier.
- A disagreement is two assertions with the same subject, attribute and period whose values cannot both be true. Assertions about different periods form a trajectory instead. The evidence ladder chooses the assertion Strata leans on: for outcome judgments, ICR Review or PPAR, then ICR, then the last ISR, then the PAD; for assertions about a moment, the record made at that moment (the PAD for appraisal ratings, each ISR for its own date, contracts and plans for dates and amounts); ties go to the more specific source, then the more recent; a report re-issued under the same number replaces its earlier version. Both assertions are always kept and shown.
- A lesson records a statement, risk factors from the closed list, a lifecycle stage, a polarity, the Regulations edition its projects followed, a state (proposed, current at a version, rejected with its reason, merged as evidence, being re-checked, retired) and versions with was, now and the reason. Its evidence rows hold the passage id, the verbatim quote, the page, and whether IEG's review restated it.

### Reading documents

- The page router sends each page down one of two routes. Route A uses the text the World Bank publishes: pages divided on form feeds, headings found from each document type's template, numbered paragraphs separated. Route B sends scanned pages, tables (PAD risk tables and procurement annexes, the ICR data sheet, ISR ratings, Procurement Plans) and figures to ai_parse_document, or to Content Understanding if day-one test 3 failed.
- A numbered paragraph is the citation unit, the way IEG cites "ICR para 54". Paragraphs over 500 tokens are divided at sentence ends. A table becomes typed rows plus one summary passage that never backs a number. Each passage keeps project, document type, version, public date, section path, paragraph number, PDF page, printed page, language and parse route, and a short header ("ICR, P130164, India, roads, III.B, ¶54, p.23") is prepended before embedding.
- Vectors from text-embedding-3-large sit in a Delta column with a Delta Sync index on Databricks AI Search; queries are hybrid (keyword and vector) with reranking and filters on project, document type, country, sector and public date. Notices' scope and qualification text is indexed as passages too, so criteria can be compared.
- Each document is parsed once. Data readiness is measured at every step (coverage by year, pages per route, read well, linked to a project, lessons verified, freshness).

### The tool registry and the tools

- Every tool follows seam 2's contract: called by name, read-only, run as the viewer, with an optional as-of date and the viewer's view; it returns rows or passages with evidence ids, public dates and source-line fields, a coverage line and, where needed, an abstention. Numbers come only from tools; a derived figure the agent needs is returned as a column.
- A row's evidence id names its table and key; a passage's names its document, version and paragraph. Ids are stable across runs, and the verifier accepts only ids returned in the current turn.
- The tools: check_plan (fixed checks on every package in a plan, with marks and data notes); find_comparables (comparables by the stated criteria, with the past range); estimate_time (the time estimate, its ranges, its track record and the precomputed what-ifs); rebidding_risk (counts of comparables advertised again, with quoted reasons); search_passages (hybrid search with filters); ask_genie (structured questions through the Genie conversation API); get_lessons (lessons ranked by fit and evidence, at their current versions); get_disagreements (disagreements and trajectories for a subject); project_signals (fixed signals for a project, with reasons and track record); data_readiness_for (the measures behind a source or an answer).
- Below 20 comparables, subgroups included, no tool returns a range or a percentage; it returns every comparable and an abstention whose sentence comes from the copy file ("I'm not giving a range: only 12 comparable packages. Here are all 12.").

### The agent and the answer contract

- Foundry prompt agents: an orchestrator for questions, and writers for the outputs each role owns (review notes on a plan, suggested PPSD risk rows, the procurement summary for the Project Paper and the mission brief for World Bank staff; PPSD risk rows and a planned date for every STEP step for implementing agencies; a lesson review writer for reviewers). Instructions are versioned in the repo and synced to Foundry the way fairshare's agent sync does it. Rules live in the instructions; messages carry data only.
- The answer loop: the app sends the question and its scope (the page's scope chip, the as-of date, the view and the language) through the Responses API; the agent returns tool calls; the app runs them as the viewer and returns the results; this repeats for at most three rounds; the agent then returns claims as JSON. Each claim is one sentence with its kind (record, quote, advice or summary), the evidence ids it rests on, the numbers and dates it states, and any quote with its passage id.
- The verifier runs on every answer, extending fairshare's to dates and quotes. (1) Every number and date matches a value in a returned row, or appears inside a quote from a cited passage that is not a table summary. (2) Every cited id came back this turn. (3) Every quote is word for word on the cited page, ignoring only whitespace and line-end hyphenation. (4) Each sentence follows from its passages, judged in one batched call and skipped where checks 1 to 3 already prove it. (5) No advice without a lesson or a comparable among its evidence. (6) A claim that rests on an assertion in a disagreement shows both sides. Sentences that fail are removed; the first is shown in the removed box with its reason and the rest are listed below it. The check line's counts come from the verifier.
- The stream carries, in order: steps (announced to screen readers as steps, never token by token), the answer's sentences with evidence ids, the evidence they cite, disagreements, the check counts, removed sentences, and a final event with the agent run id and both trace ids (Application Insights and MLflow). Every agent run is logged in strata.ops.
- Guardrails: Foundry content filters and Prompt Shields check the question and the tool results; passages are scanned when ingested and again when retrieved; tools are read-only.
- Refusals: supplier scores or profiles; fraud inferences or identifying anyone in a redacted report; comments on live tenders, prior-review decisions, evaluation reports or complaints; estimates used as inputs to award or review decisions; contract splitting to stay under review thresholds; calling anything a misprocurement; individuals' names and notice contact details; regulations quoted from the wrong edition; showing a borrower's upload outside their team. Each is answered in the first person from the copy file and each is a must-refuse benchmark question.
- Answers and drafts are written in the language the viewer asks for (French, Spanish or Portuguese as well as English); quotes stay word for word in their original language and carry their language attribute. Interface copy stays in English.

### Workflows and drafts

- Microsoft Agent Framework workflows in code: check a plan, plan a package, suggest PPSD rows, write the mission brief, review proposed lessons. The draft runtime is adapted from fairshare's, with the new states.
- A draft moves from Draft to Checked by you to Exported, and only a person moves it. Discard is set apart and undoable. Drafts are stored in strata.ops with their author's team, cite lessons at a version, show was and now when a cited lesson changes, and are blocked from export only by a version retired as wrong.
- PPSD risk rows use the Short Form columns (Risk Description, Description of mitigation, Risk Owner) unless a contract crosses the guidance's Table I thresholds, when the Long Form adds Likelihood and Impact (1 to 5), the Overall Risk Score and the Procurement Process Stage. Plan rows use STEP's own columns. Strata writes descriptions and mitigations with counts and sources as footnotes, fills planned dates only, and leaves risk owners, ratings, references and actual dates to people and STEP.
- Exports: Word in the PPSD template's columns with footnotes; a STEP row as CSV; an evidence pack as PDF and CSV that records which sources the person opened (the citations opened in the evidence drawer, per viewer and draft). Strata sends nothing itself.
- Uploaded plans and PPSDs are Official Use Only: stored with the uploader's team, filtered by team on every read path, and never retrieved for anyone else.

### Estimates

- Procurement cycle time runs from a package's specific procurement notice to its signed contract, from notices joined to awards on the STEP reference; packages still open are kept as censored.
- Comparables are chosen by stated criteria (method, category, market approach, review type, size band, region and period). The past range is Kaplan-Meier over them, drawn as one dot per comparable, hollow for open packages, switching to 20 quantile dots above about 60.
- The time estimate is an XGBoost survival model (accelerated failure time) with conformal ranges for the middle half and 8 in 10. Features are taken as of the moment a package was planned or advertised; the as-of filter keeps out signed amounts, the same project's ICR, revised dates and later ratings.
- Delay against the Procurement Plan is a survival model per STEP step with the plan as the baseline. Rebidding risk is calibrated gradient boosting compared against logistic regression, labeled experimental, from notices with no award, re-advertised notices and canceled plan rows. Project delay early warning uses fixed signals now, with a discrete-time hazard model in shadow until it beats them on the hindsight comparison. Contract modifications are not modeled: Strata says the data are not public and shows the closest public proxy (the signed amount against the plan's estimate).
- Rolling backtests train before a date and test on the next 12 months, for 2021 to 2025, and produce each time estimate's track record and its error against the past range and against the borrower's own plan. Models live in Unity Catalog with champion and challenger aliases, score in batch, and precompute every what-if combination (market approach, prequalification, lotting) so the chart answers within 100 ms. What-ifs say "went with", never "caused", and never suggest contract splitting.

### The app

- React, Vite, TypeScript, Tailwind v4 and Radix on FastAPI, from fairshare's shell, restyled to DESIGN.md, deployed as a Databricks App that acts as each viewer, with a lean requirements file.
- Navigation: the navy bar (logo, wordmark linking Home, five tabs: Packages, Projects, Lessons, Drafts, Data, and the view switch); the white band under it with the one box and the data-freshness stamp; the independent-demo footer on every screen; a skip link on every page. Every page states its purpose under its title.
- Routes, as in PLAN.md section 8: the Home briefing at the root (no model writes it); packages and a package; projects (Following, All projects); a project (Summary, Procurement, Timeline, Documents, Connections); an activity under its project by STEP reference; a document under its project at a page and paragraph; lessons with the reviewers' queue; drafts; data (Data readiness, Sources and licenses, How Strata works); and /present for the deck, which nothing links to. Any page takes evidence (open the drawer at an evidence id), view (staff by default, piu or public), asof (a date) and lang (the language of answers and drafts).
- The one box: "/" focuses it; as you type it lists what Enter will do. A P-code offers "Open", a STEP reference opens its activity, a loan number in any of its four forms opens its project, a plan offers "Check this plan"; anything else offers "Plan a package from this sentence" and "Ask this", and the person chooses. On a project or package page it carries a removable scope chip. An answer to "Ask this" opens in an answer panel under the band on the current page, scoped by the chip.
- The server applies the view's rules; a preview can only take things away; checking and exporting are disabled in previews; the preview banner never collapses. The public view shows Projects, Lessons and Data only, with no signals, time estimates or disagreements on active projects. The implementing agency view follows the roles table in the blueprint's "Navigation and roles" section. The as-of date is applied by the server to every tool and shows its own banner.
- Workspace users default to the World Bank staff view. Reviewer roles and implementing agency teams come from the roles file.
- Components come from fairshare's shell (Answer, Num, Document, Term and DefinitionWindow, Steps, Skeleton, Table, and the sse, api, store and export libraries). New components: the plan check table, the evidence drawer, the disagreement card, the check line, the coverage line, the two-lane range chart, the evidence trail, the one-hop neighbourhood, the readiness tables, the Following list, the lessons page with versions, the draft bar and the Start here strip.
- Home and project summaries render from precomputed records before any model call; the drawer opens at once; what-ifs answer within 100 ms; every route is tested on a throttled 3G connection. Below 768 px a labeled Menu holds the tabs, the drawer becomes a full-screen sheet, charts lead with their sentence, tables become cards and the neighbourhood becomes a list.
- App state lives in strata.ops with bound parameters, unless the Lakebase check in PLAN.md section 18 shows Lakebase is simpler, in which case an ADR records the switch before any app state is written. Each request logs viewer, route, view and time for the adoption measures.

### Data readiness and the dashboard

- Data readiness measures live in strata.ops per source: coverage (rows and years), linked (to projects and notices), read well (parsed cleanly, per route) and fresh (as of, and cadence), plus what each kind of question is ready for and what holds it back, and fixes ranked by what they would unlock. There is no composite score.
- One AI/BI dashboard, built from code, reads strata.ops and strata.gold, with three pages as in PLAN.md section 9: Data readiness; Governance (lineage, quality checks, personal data stripped, access where Free Edition shows it, Azure spend); and AI quality and adoption (benchmark results, Foundry evaluations, removed sentences, abstentions, retrieval precision and recall, hindsight recall as coverage times shown-when-covered, each loop's leading indicator, the share of plans anchored on Strata's ranges, weekly users, drafts checked and exported).

### Operations and learning

- The nightly job is a Declarative Automation Bundle: fetch by watermark, bronze to gold, parse and embed only what changed, sync the index, re-link, propose lessons on the Batch API, detect disagreements, score, measure data readiness, and refresh drafts that cite changed lessons. It runs at an hour away from fairshare's job and from review hours, and records each run and its quality checks.
- Three loops share one dated store, as in PLAN.md section 11 and the blueprint's "Three loops, one dated store": knowledge (trigger: a new ICR, ICR Review or PPAR; taken in nightly, decided within 10 business days; owner: a regional lead procurement specialist; gate: quote verbatim on its page and two people decide; leading indicator: days from publication to decision), retrieval (trigger: feedback with a reason and new passages; labels weekly, search tuned at most monthly; owner: the search owner with specialists judging labels; gate: no loss on the held-out or hindsight set; leading indicator: "Wrong passage" per 100 sources opened) and estimates (trigger: signings, plan actuals and drift; watched monthly, retrained quarterly; owner: the model owner co-signed by the lead; gate: wins the backtest and a quarter in shadow, and coverage holds for each Regulations edition; leading indicator: rolling coverage of the 8-in-10 range).
- Lesson governance: Strata proposes; an accredited procurement specialist recommends; a lead procurement specialist decides, by delegation from the region's accredited practice manager. IEG stays independent; its ICR Reviews are evidence at the top of the ladder, not approvals of Strata's lessons. Two people per decision, a reason for each, recusal from one's own projects, and a quarterly 10% cross-check by another region.
- Feedback writes candidate labels to strata.ops, never to production. In the pilot a person reviews every report. At scale, three agreeing users with no dissent make a silver label, weighted as in Dawid and Skene, with a 10% audit; no user supplies more than 10% of a batch; reports about one's own project always go to a person; feedback can demote a passage but never hide it. Only reviewed labels train anything, and evaluation sets never take live feedback.
- Loops through the world: every exposure is logged (STEP reference, the range shown, the option chosen), later plan rows within 14 days of Strata's value are marked as anchored, plan accuracy and duration are reported separately and compared with countries not yet onboarded, projects exposed to Strata stay out of the recall KPI, lessons are ranked by fit and evidence and never by use, and lessons and models are tagged by the Regulations edition each project follows.
- Retraining happens quarterly, or sooner if interval coverage leaves 75–85% for two months, error trails the past range by more than 10%, the input mix drifts, or a new Regulations edition takes effect, which first marks the affected lessons and models as being re-checked.
- The rollout written into the proposal: World Bank staff in two countries, then implementing agencies, then a public read-only view.

### Evaluation

- The benchmark file holds four kinds of question (SQL, documents, estimates and refusals), each with expected answers or citations.
- The retrieval set: ICR Reviews' "ICR para N" citations and PADs' "lessons reflected in the design" sections as silver labels, plus 150 queries written from award notices and judged by two people. Recall at 20, precision at 10 and nDCG at 10 are reported using only documents public before each query's date.
- The hindsight test runs on every release over the 49 slice projects with an ICR, excluding any used as extraction examples. Strata is frozen at each project's approval date and builds the risk table for the first plan's main packages; its top five risks per package are compared with the risks the completion report blamed, coded by two people with the ICR Review prevailing where they differ. The report reads "caught X of Y blamed risks across N projects (95% interval), at five per package", next to a checklist of the sector's five commonest risks. A challenger must not lose a paired comparison on the same risks (McNemar) and must beat the checklist.
- Foundry evaluations (groundedness, relevance, task adherence, tool use) run after an Entra sign-in; MLflow holds model backtests and model cards.

### Security and privacy

- Every query runs with the viewer's token and bound parameters; no SQL is built from literals. Tools are read-only.
- Contact details are stripped at ingestion; individual consultants are never named; uploads stay with the uploader's team; refusals are tested.
- Prompt Shields' false refusals on rule-like report text are avoided by keeping rules in instructions and data in messages, and a test set of real passages guards it.

### Known traps from fairshare

Ask for personal-access-token authentication explicitly when the App also exports its own credentials; the asynchronous model library needs an async key provider; the agent-framework metapackage will not install in an App, so deploy a lean requirements file; Genie stalls on a cold warehouse; Spark SQL mangles backslashes in literals; SQL tasks divide files at any semicolon outside quotes; serverless Python tasks have no file-location variable; Prompt Shields refuses data that contains rule-like sentences.

### Checks during the build

PLAN.md section 18's open checks are settled inside tickets: fairshare's nightly schedule in the bundle skeleton ticket; the exact dataset names for the attribution page in the Data readiness ticket; whether STEP exports a plan to Excel in the implementing agency drafts ticket; Lakebase against strata.ops for app state in the app shell ticket.

## Testing Decisions

- **A good test checks behaviour through one of the five seams and nothing else.** It reads like a sentence from this spec ("a plan check marks KE-NWWDA-541055-CW-RFB as Needs a look"), survives a rewrite of the code behind the seam, and never reaches inside a module, mocks an internal collaborator or checks a side channel instead of the seam's output.
- **Expected values come from an independent source of truth**, never recomputed the way the code computes them. The sources are the real documents and records in the fixtures, written down once with where each came from. From the demo plan: KE-NWWDA-541055-CW-RFB (estimated US$1,230,000.00, Pending Implementation, planned completion July 31, 2026, no signed contract); KE-NWWDA-229129-CW-RFB (estimated US$300,000, signed January 3, 2022, 186 days after its planned date, at US$1,245,092.76); KE-NWWDA-199461-GO-RFB (the reference says RFB, the Method column says Request for Quotations); KE-NWWDA-503455-CW-RFQ and KE-NWWDA-541061-CW-RFQ (Actual Amount 0.00). From the showcase: ICR ¶54 on PDF page 23 ("108 of 328 cases had to go through rebidding"); ICR ¶55 (forest and land clearances in place before awarding works contracts); ICR ¶78 (October 10, 2019); ISR 7 (August 26, 2016, Satisfactory); the mid-term review (May 16, 2016); the restructuring (July 27, 2017); ISR 12 (April 10, 2018, Moderately Unsatisfactory); IN-RRSMP-7431-CW-RFB signed June 15, 2017; the ICR Review (March 27, 2020, re-issued under the same number on May 4, 2023). Statistical expectations (Kaplan-Meier quantiles, conformal coverage, McNemar results) are computed once by an independent library on a small hand-made set and stored as literals.
- **Model outputs are recorded, not called, in the offline gate.** A recording command runs the live agent on each scripted case and saves its tool calls and claims; the scripted agent replays them. Re-recording is a deliberate act reviewed in the diff. The offline gate runs with the network off.
- **Each seam's tests:** seam 1 asserts tables and measures after a fixture run; seam 2 calls each tool with and without an as-of date and under each view, and runs the ground-truth SQL; seam 3 drives HTTP routes with the scripted agent and asserts the stream and the stored state; seam 4 runs Playwright with axe against the mocked API; seam 5 runs the harness on fixture data whose scores are known, and on the live slice for the reported numbers.
- **What the offline gate always proves:** a range or percentage never appears below 20 comparables; nothing after the as-of date is returned; a removed sentence appears in the removed box with its reason; the check line's counts match the verifier's; a preview cannot check or export; an upload never reaches another team; contact details never survive ingestion; every table has a public date; the copy file has no em dashes and none of DESIGN.md section 7's forbidden words or GLOSSARY.md's Avoid terms in user-facing strings; nothing in the app links to /present.
- **Performance budgets are tests**, not hopes: what-ifs answer within 100 ms from the precomputed grid; Home and project summaries render before any model call; every route loads on a throttled 3G profile within its budget.
- **Accessibility is tested at seam 4:** axe at WCAG 2.2 AA on every route; keyboard paths for the box, the drawer (focus moves in, Escape closes, focus returns to the marker), the range chart (one tab stop, arrow keys between marks, the plan line moved by keyboard and number input, "Show the table") and the draft bar; reflow at 320px; the language attribute on non-English passages.
- **Evaluation is separate from tests.** The benchmark, Foundry evaluations, retrieval metrics, backtests and the hindsight test produce numbers in strata.ops and MLflow; the full gate and the release gate compare them with targets and with the champion. Evaluation sets never take live feedback.
- **Prior art:** fairshare's pre-commit gate, in which the ground-truth SQL runs and the offline suite passes against a small DuckDB fixture in under two minutes, is the model for Strata's offline gate; fairshare's verifier tests are the model for the answer contract's tests; fairshare's benchmark runner, extended to the four kinds of question, is the model for the full gate. Strata adds Playwright screen tests and the replay harness, which fairshare did not have.

## Out of Scope

- Everything on the refusal list: supplier scores or profiles; fraud inferences or identifying anyone in a redacted integrity report; comments on live tenders, winners, prior-review decisions, evaluation reports or complaints; time estimates used as inputs to award or review decisions; suggesting contract splitting to stay under review thresholds; calling anything a misprocurement; individuals' names and notice contact details; regulations quoted from the wrong edition; showing a borrower's upload outside their team.
- Restricted records Strata cannot see and will not guess at: the prior-review queue, complaints, contract amendments, contract management reports and post reviews. Contract modifications are not modeled.
- Writing to STEP, sending anything to anyone, or any act that could read as a World Bank review, clearance or no-objection. Exports are files the person saves.
- Features that could come later, with conditions: debarment checks through an official API with a person confirming each match; supplier performance from the World Bank's internal data with legal approval; a Teams and Microsoft 365 Copilot channel (it would need its own tool host); a public site for contract trails; a Word add-in for drafting the PPSD; the interface in French, Spanish and Portuguese (sources, answers and drafts in those languages are in scope; interface copy is not).
- Neo4j or any second graph store (named in the proposal as the production option only); a free-form graph view; Power BI; a dark theme; maps by default.
- fairshare's deck content and figure tests, Power BI parity, dashboard JSON, synthetic data and everything airline-specific.
- An "About this demo" page in the footer: the blueprint lists it as the owner's call, undecided, so it is not built unless the owner decides to add it.
- Gap fills whose day-one test passed.

## Further Notes

- **Dates that bind the build:** the free Azure credit ends November 10, 2026, so pay-as-you-go comes first; P156634 closes October 31, 2026, so its signals are rechecked on demo day and P130164 stays the closed showcase; Foundry portal workflows retire December 1, 2026 and are not used; apps stop 24 hours after each deploy, which the demo-ready command handles.
- **Wireframe numbers.** Rows, numbers, dates and quotes in the blueprint are real where a source is named; the rest are marked illustrative (for example the 37 comparables, the 118 packages in the track record, the 6 of 31 completion reports). Illustrative numbers must never ship as findings: every number on a screen, in the proposal or in the deck comes from a tool, a measure or the replay harness.
- **Phases.** P0 foundations end when every day-one test has a result and a chosen path. P1, the walking skeleton, ends when the deployed app checks one plan and answers one question with citations and the offline gate runs in under two minutes. P2 deepens in rubric order (architecture, AI method, domain, operations) and ends when benchmark targets are met or each gap is written down. P3 ends when nothing in the proposal is a number that was not measured. P4 ends when each change drill lands in under ten minutes with the gate green.
- **Designed, not built.** If time runs short, anything unfinished is labeled "designed, not built" in the app, the proposal and the deck, and listed in the proposal's short list of what is designed but not built.
- **Rubric map.** System and knowledge architecture (30): six sources, the page router, numbered passages, the Unity Catalog knowledge model with edges and dated assertions, entity resolution. Analytical and AI methodology (30): the survival model with calibrated ranges and backtests, agentic retrieval over SQL, hybrid search and the graph, six checks, the evidence ladder, the hindsight test. Domain alignment and data use (25): the borrower's PPSD and Procurement Plan as the decision, checked row by row; STEP's words and formats; the 2025 Regulations; the FY2017–19 gap and contract modifications handled honestly. Operationalization and scalability (15): nightly incremental jobs, three loops with gates, KPIs, a phased rollout, cost caps, the change drill.
- **Words.** GLOSSARY.md governs every term in code names, copy, the proposal and the deck. Copy follows DESIGN.md section 7, including "World Bank" never "the Bank" outside fixed terms, "Procurement Plan" in full, STEP's field names and values word for word, and the current Regulations' names for selection methods.
