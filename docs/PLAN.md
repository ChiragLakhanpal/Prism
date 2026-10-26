# Strata build plan

Agreed in planning on October 22, 2026, after three rounds of questions and a design review. The visual version, with the wireframes and the reasoning behind each screen, is the Strata Blueprint artifact (https://claude.ai/artifact/CNZhzdhRRz2RwTXichTKAs). Decisions with lasting consequences are in `docs/adr/`, the words are in `GLOSSARY.md`, and the look and copy rules are in `DESIGN.md`. Nothing here has been built yet.

## 1. What we are building

Strata is procurement intelligence on World Bank open data. It links what happened in past procurements (the What stratum) to how they were carried out (How) and why they succeeded or failed (Why), so the people who plan, design, monitor and learn from procurement see the evidence behind every answer.

- **Who owns what.** The borrower prepares the PPSD and the Procurement Plan; the plan lives in STEP. The World Bank's procurement specialist supports the borrower, assesses the implementing agency's procurement risk, clears the plan and writes the procurement section of the Project Paper. Strata follows that split, and nothing it produces is a World Bank decision.
- **Users, in order:** World Bank procurement specialists and task team leaders; borrowers' implementing agencies (PIU, PMU or PCU locally); the public, read-only.
- **Ways in:** "Check a plan" is the lead entry, on a published plan or, for an implementing agency, a private upload of a STEP export. "Plan a package from a sentence" serves concept stage, before any STEP rows exist. Task team leaders get a mission brief.
- **Scope:** every lifecycle stage (planning and strategy, tender design and packaging, execution and monitoring, continuous learning) and every assessment module, built.
- **Deliverables:** the app, deployed as a Databricks App, with the deck at `/present` and no link to it in the app (its URL goes in the proposal and the README); the proposal, written by module with every number linked to a measured result; one AI/BI dashboard.
- **Round 2 of the interview:** the panel will ask for live code changes and judges every rubric dimension, so changeability is a requirement (section 15).

## 2. Platform

| Piece | Where | Notes |
|---|---|---|
| Lakehouse, knowledge model, search, Genie, models, app, dashboard | Databricks Free Edition, the workspace fairshare also uses | Strata has its own catalog, `strata`, with its own medallion schemas, pipelines and nightly job |
| Agent, guardrails, evaluations, agent traces | Microsoft Foundry project `Strata` on `wb-strata`, resource group `WorldBank-demo` | ADRs 0001 and 0003 |
| Models | Azure OpenAI deployments in `wb-strata` | `gpt-5.4-mini` for the agent, `gpt-5.4` for drafting and hard questions, `gpt-5.4-nano` on Global Batch for bulk extraction, `text-embedding-3-large` at 1,024 dimensions |
| Gap fills, only if a day-one test shows the gap | Azure | A Container Apps job for ingestion; Content Understanding `prebuilt-layout` for parsing; a Container Apps copy of the app behind Entra sign-in for reviewers |
| Code | A new private GitHub repo, `strata` | Reviewers added as collaborators |

**Shared workspace limits.** Free Edition limits are per account, so Strata and fairshare share them: 3 apps (one each), one AI Search endpoint (Strata's), one 2X-Small SQL warehouse, 5 concurrent job tasks and one daily compute quota. Apps stop 24 hours after each start or deploy. The two nightly jobs run at different hours.

**Azure billing.** About US$197 of free credit lasts until November 10, 2026, and the subscription moves to pay-as-you-go before then. Budgets only alert, so hard caps do the work: a tokens-per-minute limit on each deployment, a daily page cap in ingestion, at most two replicas for anything hosted, and paid resources deleted after the pilot. There is no fallback model.

## 3. Data

### Sources

| Source | Endpoint | Use |
|---|---|---|
| Contract awards since FY2020 | Finances One `DS00005` / `RS00005` | All IPF awards, prior and post review, from STEP; about 296,000 supplier rows, updated daily |
| Contract awards FY2001–16 | Finances One `DS01004` / `RS00934` | Prior review only; frozen since March 2022 |
| IEG ratings | Finances One `DS00053` / `RS00055` | Outcome and Bank performance for 12,629 projects |
| Loans and credits | Finances One `DS00001` and `DS00047` (latest); `DS00976` and `DS00975` (monthly history, slice only) | Disbursed and canceled amounts; closing-date history |
| Procurement notices | `search.worldbank.org/api/v2/procnotices` | 423,830 notices; award notices list every bidder, prices and rejection reasons |
| Projects | `search.worldbank.org/api/v3/projects` | Dates, sectors, ESF risk, implementing agency, latest ISR ratings, loan transactions |
| Documents | `search.worldbank.org/api/v3/wds` | PAD, ISR, ICR, ICR Review, PPAR, Procurement Plan, Project Paper (restructurings) and CPF, each with `txturl` and `pdfurl` |
| CPIA and WGI | `api.worldbank.org/v2` | `IQ.CPA.*` (IDA countries only); `GOV_WGI_*` (the old `GE.EST` codes no longer work) |
| Procurement rules and templates | Documents & Reports and worldbank.org's procurement framework pages | Procurement Regulations, 7th edition (September 2025); the PPSD Short and Long Form templates and guidance; the Procurement Plan template (English and French) |

Finances One answers at `https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=…&resourceId=…&type=json&top=&skip=`. The old finances.worldbank.org Socrata API is gone. Use the v3 search APIs; the v2 projects and documents APIs are stale.

### Scope

- **Structured data, everywhere:** all awards, notices, projects, IEG ratings, loan snapshots and indicators, under 0.5 GB in total.
- **Documents, for the pilot slice:** Kenya, Bangladesh, Vietnam and Pakistan, water and transport, approved FY2012–2025. That is 128 projects, 4,810 contract rows, 1,064 ISRs, 49 ICRs, 43 ICR reviews and 2,909 procurement-plan versions: about 43,000 pages before keeping only the latest plan per implementing agency.
- **Showcase:** India Rajasthan Road Sector Modernization (P130164), for its documented disagreement (ISR 7 against ICR ¶78) and its rebidding lesson (ICR ¶54).
- **Demo plan:** the Northern Water Works Development Agency's October 9, 2026 plan for the Kenya Water and Sanitation Development Project (P156634). It closes October 31, 2026, so recheck its signals on demo day.
- **Stress shelf:** the P130164 PAD (a 100-page scan with a garbled two-column risk annex); the longest PAD in the slice; a procurement plan with hundreds of rows; a completion report in French; a document over 500 pages, if one exists.

### Joins

- `project_id` joins everything at project level.
- The STEP reference (for example `KE-MOWASCO-16771-CW-RFB`) joins a notice's `bid_reference_no`, an award's `borrower_contract_reference_number` and a plan's activity reference. About 64% of recent awards carry one. Read the method from the plan's Method column, not from the reference.
- The STEP supplier ID in award notices usually equals the awards table's `supplier_id`, but not always. In the fixture, 157 awarded bidders have the same name as a supplier on the award rows of their STEP reference. Of those, 29 carry another ID (`tests/ground_truth/values.toml`, `[counts.supplier_ids]`). Each ID stays as written, two IDs are never merged by name, and `strata.ops.data_readiness` measures how often they agree (`awarded_bidder_id_on_award` and `awarded_bidder_id_same_name`).
- Loan numbers come in five forms (`IDA60290`, `IDA-60290`, `60290`, `IDA / 60300`, and the older four-digit number with a country code, `6030-KE`, which is credit `IDA60300`); normalize them once.
- Country and year join CPIA and WGI, lagged to what had been published at the time.

### Quirks to handle on purpose

Fiscal years run July to June. Dates come in mixed formats, and some document dates are in the future. Awards for FY2017–19 are in neither dataset; award notices fill most of the gap, in local currency. A joint venture appears as one row per member with the amount split equally. "INDIVIDUAL CONSULTANT" hides many supplier IDs. Awards are in US dollars, notices and plans in local currency. Two sector taxonomies coexist. The projects API keeps only the latest ISR ratings, with duplicates. Plain text scrambles procurement-plan tables, and some signed rows show an Actual Amount of 0.00. Plan updates re-date steps, so delay is measured from the first published planned date. Notices carry contact names, emails and phone numbers, which are stripped at ingestion.

## 4. Unity Catalog layout

| Schema | Holds |
|---|---|
| `strata.bronze` | API pages as received, with fetch time and source; the volume `strata.bronze.files` for PDFs and text files |
| `strata.silver` | Typed, cleaned tables per source; parsed document elements: pages, sections, passages, table rows |
| `strata.gold` | The knowledge model (country, project, package, notice, contract, contract supplier, supplier, document, passage, lesson and its versions, lesson evidence, risk factor, assertion, disagreement, edge), metric views for Genie, features and scores |
| `strata.ops` | Data readiness measures, pipeline runs, agent runs, drafts and their states, feedback and candidate labels, exposure logs, evaluation results, cost |

Every row keeps the date it became public (ADR 0002). Assertions also keep the period they describe and when they were made. Bronze and silver are rebuilt from source and never edited by hand. App state lives in `strata.ops` with bound parameters, as in fairshare. Uploaded plans and PPSDs are Official Use Only: they stay with the uploader's team and are never retrieved for anyone else.

## 5. Turning documents and records into evidence

- **Page router.** Route A uses the text the Bank publishes: split pages on form feeds, find headings from each document type's template, split numbered paragraphs. Route B sends scanned pages, tables (PAD risk tables and procurement annexes, the ICR data sheet, ISR ratings, procurement plans) and figures to `ai_parse_document`, or to Content Understanding if Free Edition lacks it.
- **Passages.** A numbered paragraph is the citation unit, the way IEG cites "ICR para 54". Paragraphs over 500 tokens split at sentence ends. A table becomes typed rows plus one summary passage that never backs a number. Each passage keeps project, document type, version, public date, section path, paragraph number, PDF page, printed page, language and parse route. A short header ("ICR, P130164, India, roads, III.B, ¶54, p.23") is prepended before embedding.
- **Search.** `text-embedding-3-large` vectors in a Delta column, a Delta Sync index on Databricks AI Search, hybrid queries with reranking, and filters on project, document type, country, sector and public date.
- **Lessons.** One batch pass over each ICR, ICR review and PPAR proposes lessons with a statement, risk factors from a closed list, a lifecycle stage, a polarity and verbatim evidence. A proposed lesson is rejected unless its quote is found on the cited page. An ICR Review's restatement becomes a second, IEG-endorsed piece of evidence. Proposed lessons wait for review (section 11).
- **Suppliers.** STEP supplier IDs come first. Names are matched (Splink) only where no ID exists, with a model adjudicating the uncertain middle and a person deciding whatever stays uncertain. A joint venture is its own supplier, linked to its members. Target: auto-merge precision of at least 0.98 on 1,000 labeled pairs.
- **Links.** A contract links to a passage through a scored edge (project, sector, time, text similarity, shared mentions), shown to users as "appeared together", never as cause.
- **Assertions and disagreements.** Ratings, dates and amounts become assertions. A disagreement is two assertions about the same thing for the same period that cannot both be true; a rating that changes over time is a trajectory. Outcome judgments lean on ICR Reviews and PPARs, then the ICR, then the last ISR. Facts about a moment lean on the record made at that moment. Ties go to the more specific, then the more recent source. Both sides always show, in date order.

## 6. Agent, tools and checks

- **Agents in Foundry**, with instructions versioned in the repo and synced the way fairshare's `foundry.py` does it: an orchestrator for questions, and writers for the outputs each role owns. For World Bank staff: review notes on a plan, suggested risk rows for the borrower's PPSD, the procurement summary for the Project Paper, a mission brief. For implementing agencies: PPSD risk rows and a planned date for every STEP step. Lesson review is a reviewers' writer. Rules live in the instructions; messages carry data only.
- **Tools run in the app as the viewer** (ADR 0003): `check_plan`, `find_comparables`, `estimate_time`, `rebidding_risk`, `search_passages`, `ask_genie`, `get_lessons`, `get_disagreements`, `project_signals` and `data_readiness_for`. Every tool takes an optional as-of date.
- **Workflows in Microsoft Agent Framework**, in code: check a plan, plan a package, suggest PPSD rows, write the mission brief, review proposed lessons. Every draft moves from Draft to Checked by you to Exported, and only a person moves it.
- **Formats.** PPSD risk rows use the Short Form template (Risk Description, Description of mitigation, Risk Owner) unless a contract crosses the guidance's Table I thresholds, when the Long Form adds Likelihood and Impact (1 to 5), the Overall Risk Score and the Procurement Process Stage. Plan rows use STEP's own columns. Strata writes descriptions and mitigations with counts and sources as footnotes, fills planned dates only, and leaves risk owners, ratings, references and actual dates to people and STEP.
- **The verifier**, fairshare's extended to dates and quotes, runs on every answer: every number matches a returned row; every cited id came back this turn; every quote is on the cited page; each sentence follows from its passages (one batched judge call, skipped where the first three already prove it); no advice without a lesson or comparable; disagreements show both sides. Sentences that fail are removed and the first one is shown under the answer.
- **Guardrails.** Foundry content filters and Prompt Shields check the question and the documents; passages are scanned when ingested; tools are read-only.
- **Refusals**, each a must-refuse benchmark question: supplier scores or profiles; fraud inferences or identifying anyone in a redacted report; comments on live tenders, prior-review decisions, evaluation reports or complaints; estimates used as decision inputs; contract splitting to stay under review thresholds; calling anything a misprocurement; individuals' names and notice contact details; regulations quoted from the wrong edition; showing a borrower's upload outside their team. Some could become features later under conditions (debarment checks through an official API with a person confirming each match; supplier performance from the Bank's internal data with legal approval).

## 7. Estimates

| Estimate | Built from | Method | Status |
|---|---|---|---|
| Procurement cycle time, notice to signed contract | Notices joined to awards on the STEP reference; packages still open kept as censored | Kaplan-Meier past range; XGBoost survival model (AFT) for the time estimate, with conformal ranges | Build |
| Delay against the Procurement Plan | Planned and actual dates per STEP step, from the first published planned date | Survival model per step, with the plan as the baseline | Build |
| Rebidding risk | Notices with no award, re-advertised notices, canceled plan rows | Calibrated gradient boosting against logistic regression | Build, labeled experimental |
| Project delay early warning | ISR history, closing-date extensions, restructurings, disbursement, plan dates | Fixed signals now; a discrete-time hazard model in shadow until it beats them on the hindsight test | Build |
| Contract modifications | No public record | None; Strata says so and shows the closest proxy | Not modeled |

Rolling backtests train before a date and test on the next 12 months, for 2021 to 2025. Each time estimate shows its track record ("of 118 packages from 2025 Strata had not seen, 93 finished inside its 8-in-10 range"), error against the past range and against the borrower's own plan, and Strata abstains below 20 comparables, subgroups included. Features are taken as of the moment a package was planned or advertised; the as-of filter keeps out leakage (signed amounts, the same project's ICR, revised dates, later ratings). Models live in Unity Catalog with champion and challenger aliases and score in batch, with every what-if combination precomputed so the chart answers within 100 ms. What-ifs cover market approach, prequalification and lotting, say "went with", never "caused", and never suggest splitting a contract.

## 8. The app

- React, Vite, TypeScript, Tailwind v4 and Radix on FastAPI, from fairshare's shell, restyled to `DESIGN.md` and deployed as a Databricks App that acts as each viewer.
- **Navigation:** five tabs (Packages, Projects, Lessons, Drafts, Data), one box on every page that says what Enter will do, and the project page as the hub. A view switch previews the implementing agency and public views honestly: the server applies that view's rules, a preview can only take things away, and checking and exporting are disabled in previews.
- **Routes:** `/` (the briefing; no model writes it), `/packages`, `/packages/:id`, `/projects` (Following, All projects), `/projects/:pid` (Summary, Procurement, Timeline, Documents, Connections), `/projects/:pid/packages/:stepRef`, `/projects/:pid/documents/:doc?page=&para=`, `/lessons?stage=&method=&sector=&status=&page=&show=` (the library's filters, its page, and `show`, which opens the page that holds a lesson; and a reviewers' queue; for passage reviewers, Passage reports at `/lessons/reports` and `/lessons/reports/:groupId`; for query judges, Judging at `/lessons/judging?show=&page=` and `/lessons/judging/:queryId?p=`), `/drafts`, `/data` (Data readiness, Sources and licenses, How Strata works), and `/present` (the deck; nothing links to it). Any page takes `?evidence=`, `?view=`, `?asof=` and `?lang=`; `?evidence=versions:{lesson_id}:{a}:{b}` opens two versions of a lesson in the drawer (ticket 39).
- **From fairshare:** `Answer`, `Num`, `Document`, `Term` and `DefinitionWindow`, `Steps`, `Skeleton`, `Table`, and the `sse`, `api`, `store` and `export` libraries. New: the plan check table, the evidence drawer, the disagreement card, the check line, the coverage line with its denominator, the two-lane range chart, the evidence trail and one-hop neighbourhood, the readiness tables, the Following list, the lessons page with versions, the draft bar, the Start here strip.
- **Exports:** Word in the PPSD template's columns with footnotes, a STEP row (CSV), an evidence pack (PDF and CSV) that records which sources the person opened. Strata sends nothing itself.
- All copy lives in one file and follows `DESIGN.md` section 7. The World Bank logo and the independent-demo footer follow sections 8 and 9.

## 9. Dashboard

One AI/BI dashboard, built from code, reading `strata.ops` and `strata.gold`:

- **Data readiness:** coverage, link rates, read-well rates, freshness, and fixes ranked by what they unlock.
- **Governance:** lineage, quality checks, personal data stripped, access where Free Edition shows it, Azure spend.
- **AI quality and adoption:** benchmark results, Foundry evaluations, removed sentences, abstentions, retrieval precision and recall, hindsight recall (coverage times shown-when-covered), each loop's leading indicator, the share of plans anchored on Strata's ranges, weekly users, drafts checked and exported.

## 10. Evaluation and the gate

- `evals/benchmark.yaml` holds four kinds of question (SQL, documents, estimates and refusals), each with expected answers or citations.
- A retrieval set built cheaply: ICR Reviews' "ICR para N" citations and PADs' "lessons reflected in the design" sections serve as silver labels, plus 150 queries written from award notices and judged by two people. Report recall at 20, precision at 10 and nDCG at 10, using only documents public before each query's date. Evaluation sets never take live feedback.
- **The hindsight test**, run on every release: the 49 slice projects with an ICR. Strata is frozen at each project's approval date and builds the risk table for the first plan's main packages; its top five risks per package are compared with the risks the completion report blamed, coded by two people, with the ICR Review prevailing where they differ. Report "caught X of Y blamed risks across N projects (95% interval), at five per package", next to a checklist of the sector's five commonest risks. A challenger must not lose a paired comparison on the same risks (McNemar) and must beat the checklist. Projects used as extraction examples are excluded.
- Foundry evaluations (groundedness, relevance, task adherence, tool use) after an Entra sign-in; MLflow for model backtests and model cards.
- The pre-commit gate from fairshare: the ground-truth SQL runs and the tests pass offline against a small DuckDB fixture in under two minutes. A full gate adds the Genie benchmark and the Foundry evaluations.

## 11. Operations and learning

- **Nightly job**, as a Declarative Automation Bundle: fetch by watermark, bronze to gold, parse and embed only what changed, sync the index, re-link, propose lessons on the Batch API, detect disagreements, score, measure data readiness, and refresh drafts that cite changed lessons.
- **Three loops, one dated store.**

  | | Knowledge | Retrieval | Estimates |
  |---|---|---|---|
  | Trigger | A new ICR, ICR Review or PPAR | Feedback with a reason; new passages | Signings and plan actuals; drift |
  | Cadence | Taken in nightly; decided within 10 business days | Labels weekly; search tuned at most monthly | Watched monthly; retrained quarterly |
  | Owner | A regional lead procurement specialist | The search owner, with specialists judging labels | The model owner, co-signed by the lead |
  | Gate | Quote verbatim on its page; two people decide | No loss on the held-out or hindsight set | Wins the backtest and a quarter in shadow; coverage holds for each Regulations edition |

- **Lesson governance.** Strata proposes; an accredited procurement specialist recommends; a lead procurement specialist decides, by delegation from the region's accredited practice manager. IEG stays independent: its ICR Reviews are evidence at the top of the ladder, not approvals. Two people per decision, a reason for each, recusal from one's own projects, and a quarterly 10% cross-check by another region. States: proposed, current at a version, rejected (reason kept), merged as evidence, being re-checked, retired. Drafts cite a lesson version and show was and now when it changes.
- **Feedback** writes candidate labels to `strata.ops`, never to production. In the pilot a person reviews every flag. At scale, three agreeing users with no dissent make a silver label (weighted as in Dawid and Skene), with a 10% audit; no user supplies more than 10% of a batch, and flags about one's own project always go to a person. Only reviewed labels train anything.
- **Loops through the world.** Strata logs every exposure (STEP reference, the range shown, the option chosen) and marks later plan rows within 14 days of its value as anchored, so plan accuracy and duration are reported separately and compared with countries not yet onboarded. Projects exposed to Strata stay out of the recall KPI. Lessons are ranked by fit and evidence, never by use. Lessons and models are tagged by the Regulations edition each project follows.
- **Retraining** quarterly, or sooner if interval coverage leaves 75–85% for two months, error trails the past range by more than 10%, the input mix drifts, or a new Regulations edition takes effect, which first means "flag and re-check".
- **Rollout, for the proposal:** World Bank staff in two countries, then implementing agencies, then a public read-only view.
- **A demo-ready command** starts the app, warms the warehouse and asks one smoke question.

## 12. What comes from fairshare

Copy, never import: the repos stay separate.

- **As is:** `fairshare/dbx.py` (viewer identity), `harness/facts.py` and `aio.py`, the server's identity and stream routes, `lakehouse/app_deploy.py`, `.githooks/pre-commit`, the destructive-command hook, and the rules in `CLAUDE.md`.
- **Adapt:** `db.py` (bound parameters instead of hand-built literals), `verifier.py` (dates and quotes), `tools.py` (the Genie client), `agents.py` (the draft runtime, with the new states), `clauses.py` (lesson proposals), `genie.py` (the Genie space from code), `foundry.py` (agent sync and evaluations), the benchmark runner, and the web shell and its components.
- **Leave:** the deck's content and figure tests, Power BI parity, the dashboard JSON, the synthetic data, and everything airline-specific.
- **Known traps** from fairshare's `docs/limits.md`: pass `auth_type="pat"` when the App also exports its own credentials; the async model client needs an `async` key provider; the agent-framework metapackage will not install in an App, so deploy a lean requirements file; Genie stalls on a cold warehouse; Spark SQL mangles backslashes in literals; SQL tasks split files at any semicolon outside quotes; serverless Python tasks have no `__file__`; Prompt Shields refuses data that contains rule-like sentences.

## 13. Phases

| Phase | Work | Done when |
|---|---|---|
| P0 Foundations | Repo with rules, hooks and the gate; the `strata` catalog; the day-one tests; model deployments; Azure caps; pay-as-you-go before November 10 | Every day-one test has a result and a chosen path |
| P1 Walking skeleton | Every stage and module, thinly: one country ingested, one published plan checked, 20 documents read, comparables and a past range, one cited answer through the Foundry agent and the verifier, the Data readiness page, one dashboard page, the deployed app | The deployed app checks one plan and answers one question with citations, and the offline gate runs in under two minutes |
| P2 Deepen, in rubric order | Architecture: the full slice, entity resolution, edges, assertions, disagreements, the stress shelf. AI method: the survival model and backtests, hybrid retrieval with the labeled set, all six checks, Foundry evaluations, the hindsight test. Domain: review notes and PPSD rows in the templates' columns, STEP's words, signals for projects you follow, the lesson review, other languages. Operations: the nightly job, the three loops, all three dashboard pages, KPIs | Benchmark targets are met, or each gap is written down |
| P3 Proposal and deck | The proposal by module; the deck at `/present` in World Bank style, with diagram-design and hairline figures; a list of what is designed but not built | Nothing in the proposal is a number that was not measured |
| P4 Change drills and rehearsal | About ten change requests rehearsed; the demo-ready command; a full run-through | Each drill lands in under ten minutes with the gate green |

## 14. Day-one tests

1. Free Edition reaches `search.worldbank.org`, `documents1.worldbank.org`, `datacatalogapi.worldbank.org` and `api.worldbank.org` from a notebook, a job and the app. If not, ingestion runs as a Container Apps job that pushes files into the volume.
2. Free Edition reaches the Foundry and Azure OpenAI endpoints from a job, not only from the app.
3. `ai_parse_document` runs on a 120-page PAD. If not, Content Understanding parses.
4. An AI Search endpoint and a hybrid index can be created.
5. The Genie conversation API answers as the token's user.
6. An outside email can join the workspace and open the app. If not, a Container Apps copy of the app runs behind Entra sign-in.
7. A personal access token or a service principal can be created.
8. The four models deploy within the subscription's quota.
9. Foundry evaluations run after an Entra sign-in.
10. Traces reach Application Insights from the app.

## 15. Change drill

Add a data source; add a tool; change a signal threshold; add a country to the slice; swap the model; reorder the evidence ladder; add a field to the package form; reword copy; add a benchmark or must-refuse question; add a dashboard tile. Each lives in one place (a registry, a config file, the copy file or the benchmark), so each lands in under ten minutes.

## 16. Risks

| Risk | Response |
|---|---|
| Free Edition cannot reach the World Bank hosts | A Container Apps job pushes files into the volume |
| The daily quota stops compute during a review | Parse each document once, run the two nightly jobs apart and away from review hours, warm everything before reviews |
| The app stops 24 hours after a deploy | The demo-ready command restarts and warms it |
| The free credit ends on November 10 | Pay-as-you-go before then, with alerts and caps |
| Prompt Shields flags real report text | Rules in instructions, data in messages, and a test set of real passages |
| Supplier names matched wrongly | IDs first, no supplier scores, and a person decides uncertain matches |
| The demo plan's project closes October 31 | Recheck the P156634 signals on demo day; keep P130164 as the closed showcase |
| "Build complete" outruns the time | Walking skeleton first; anything unfinished is labeled "designed, not built" |

## 17. Rubric map

| Dimension | Points | Where Strata earns it |
|---|---|---|
| System and knowledge architecture | 30 | Six sources, the page router, numbered passages, the Unity Catalog knowledge model with edges and dated assertions, entity resolution |
| Analytical and AI methodology | 30 | The survival model with calibrated ranges and backtests, agentic retrieval over SQL, hybrid search and the graph, six checks, the evidence ladder, the hindsight test |
| Domain alignment and data use | 25 | The borrower's PPSD and Procurement Plan as the decision, checked row by row; STEP's own words and formats; the 2025 Regulations; the FY2017–19 gap and contract modifications handled honestly |
| Operationalization and scalability | 15 | Nightly incremental jobs, three learning loops with gates, KPIs, a phased rollout, cost caps, the change drill |

## 18. To check during the build

- fairshare's nightly job schedule, so Strata's runs at a different hour.
- The exact dataset names for the attribution page.
- That STEP can export a plan to Excel for the implementing agency's private upload. Settled in ticket 38 on October 25, 2026: it could not be confirmed, since STEP's help sits behind its sign-in and no public page describes an export, and no STEP Excel file is recorded, so there is no parsed sample. The World Bank's Procurement Plan template is a text template whose tables live in STEP. So Strata reads the fallback: the columns of the plan tables that every published Procurement Plan prints, as `src/strata/reader/step.py` records them, set out as a published plan sets them out or in one header row. `config/uploads.toml` records this answer and the layouts, and its `format` value picks the upload page's hint.
- Whether a Lakebase project would be simpler than `strata.ops` for app state on Free Edition.
