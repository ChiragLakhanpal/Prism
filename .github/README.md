<h3 align="center">Strata is procurement intelligence on World Bank open data, with every claim cited.</h3>

[![A 22-second silent film of Strata, made from real screens of the app: a question about a package, the cited answer and its checks, a borrower's plan checked row by row, and a timeline where reports disagree.](/docs/readme/strata-film.webp)](/docs/readme/strata-film.mp4)

<p align="center"><sub>Silent, 22 seconds, real screens from the live app. Select the film to open the full-quality MP4.</sub></p>

## Ask about any package

Ask a question in plain words. Strata answers from World Bank records and documents, and each sentence names its source. Before you see the answer, a verifier checks every number against the records. It removes any sentence it can't back and shows you why.

![A cited answer about how long comparable packages took, with numbered sources, the checks it passed and one sentence it removed, beside the package's procurement steps.](/docs/readme/answer.webp)

## Check a borrower's plan, row by row

Strata reads a borrower's Procurement Plan from its latest published version. It checks each activity against past ranges, review thresholds and the plan's own dates. A row marked Watch is a reason to look, never a finding, and it names the record behind it.

![The activities in a Kenyan agency's Procurement Plan, each with its method, review type, estimate, status and what Strata found.](/docs/readme/plan.webp)

## See how long packages like this one took

Comparable packages give the past range, from each notice to its signed contract. Packages still open stay in the range, so it keeps the slow cases. A survival model gives the time estimate, and with no model or too few packages, Strata says why instead of guessing.

![The past range for 150 comparable packages, from notice to signature, beside the package's row in its plan.](/docs/readme/range.webp)

## See where reports disagree

Reports written before, during and after a project don't always agree. Strata puts each disagreement on one timeline and keeps both reports on screen. It says which one it leans on, and why.

![A project timeline where dashed lines join the reports that disagree, over the ratings of progress from each status report.](/docs/readme/timeline.webp)

## Read a project in a few sentences

Each project opens on a short summary of its dates, money and ratings. Every figure cites its record, and one click opens it.

![A project summary in plain sentences, above tables of dates and money where every figure cites its record.](/docs/readme/summary.webp)

## Lessons that people decide

Strata proposes lessons from completion reports and quotes each one word for word, with its page. An accredited procurement specialist recommends each lesson, and a different lead procurement specialist decides. Nothing enters the library until a lead decides.

![A proposed lesson with its quote highlighted on the page it came from, the check that found it word for word, and what has happened so far.](/docs/readme/lessons.webp)

## It says what it can't answer yet

The Data page shows what each kind of question is ready for and what holds it back. When a source has no measures yet, Strata says so instead of giving a headline.

![The Data page, which opens by saying it gives no headline yet, above a table of what you can ask and what holds each answer back.](/docs/readme/data.webp)

## How it scored

These results come from the full gate of November 1, 2026. Each number is in [docs/proposal/snapshot.json](/docs/proposal/snapshot.json), with the run that measured it.

![27 of 43 benchmark questions passed, 11 of 11 must-refuse questions turned down, 25 of 25 answers rated grounded by Foundry's evaluator, and 4,154 numbered passages.](/docs/readme/results.webp)

## How it's built

A nightly job turns World Bank open data and documents into one dated knowledge model on Databricks. The app runs every tool as the person asking. An agent in Microsoft Foundry picks the tools and writes the answer, and the verifier checks every sentence before anyone sees it.

![The architecture: public sources feed a nightly job into bronze, silver, gold and ops tables on Databricks, with a search index, a Genie space, models in MLflow and a dashboard. The Databricks App runs the tools and the verifier, keeps its state in Lakebase, and trades tool calls with an agent in Microsoft Foundry.](/docs/readme/architecture.webp)

## The presentation

The 28-slide deck covers the problem, a live demo, how Strata is built, how it answers and how it would grow.

[![The deck's title slide in front of two of its slides.](/docs/readme/presentation.webp)](/docs/presentation/strata-presentation.pdf)

**[Download the presentation (PDF, 28 slides, 1.4 MB)](/docs/presentation/strata-presentation.pdf)**

## Run it

The developer guide, [README.md](/README.md) at the root of the repo, covers installing, the gate, running the app on your computer and deploying it to a Databricks workspace.

<sub>Strata is an independent demo built on World Bank open data. It is not a World Bank product, and the World Bank has not reviewed or endorsed it. Built by Chirag Lakhanpal.</sub>
