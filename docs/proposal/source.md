# Strata: a technical proposal

Strata is procurement intelligence on World Bank open data, built for the World Bank Group's procurement intelligence assessment. This proposal follows the four modules of the assessment. Every number in it links to the result the build measured or to the setting that fixes it.

{copy:footer}

{datasheet}

**How to read it.** Paragraphs are numbered, as in a World Bank project document, so you can point to one. A number links to [Annex 1](#sec-annex-results), which names the run or query that produced it, or to [Annex 2](#sec-annex-settings), which names the file that sets it and the test that enforces it.

{when:designed} Anything marked "Designed, not built" is described here but is not in Strata yet, and [the list after Module 4](#sec-designed-not-built) names each one.

## Summary {#summary}

{#summary-what} Strata checks a borrower's Procurement Plan against what happened to packages like it. It links the World Bank's contract awards, procurement notices and project records to the completion reports and supervision reports that say why a procurement went well or badly. Every claim cites a record or a numbered paragraph with its page, and every number comes from a tool.

{#summary-who} Strata serves World Bank procurement specialists and task team leaders first, then implementing agencies. The decision it supports is the borrower's own. Strata checks the borrower's Procurement Plan and Project Procurement Strategy for Development (PPSD) package by package. The borrower prepares the plan, and nothing Strata produces is a World Bank decision.

{#summary-how} Strata keeps its data in Databricks and its agent in Microsoft Foundry. The agent picks tools, the app runs each tool as the person asking, and a verifier checks every sentence before anyone reads it. {fig:pipeline} shows the parts.

{#summary-measured} The table gives results for each rubric dimension. [Annex 1](#sec-annex-results) lists every result in this proposal with the run or query that produced it.

### What the build measured {#summary-table}

| Dimension | Result | Measured | Explained in |
|---|---|---|---|
| System and knowledge architecture | Strata read {r:pages-read-well} pages of the slice's documents well. | {r:pages-read-well\|measured_on} | {sec:m1-long-reports} |
| System and knowledge architecture | {r:linked-notice} contract award rows since fiscal 2020 carried a STEP reference that a procurement notice also carried. | {r:linked-notice\|measured_on} | {sec:m1-taking-in} |
| Analytical and AI methodology | {r:backtest-coverage} test packages were signed within the 8-in-10 point of their range. | {r:backtest-coverage\|measured_on} | {sec:m2-time-estimates} |
| Analytical and AI methodology | {r:benchmark-passed} benchmark questions passed, and the verifier removed {r:sentences-removed} sentences. | {r:benchmark-passed\|measured_on} | {sec:m3-checks} |
| Domain alignment and data use | Strata built {r:gap-contracts} contracts for fiscal 2017 to 2019 from award notices, the years no awards dataset covers. | {r:gap-contracts\|measured_on} | {sec:m1-taking-in} |
| Domain alignment and data use | Ingestion removed contact details from {r:contacts-removed} procurement notices. | {r:contacts-removed\|measured_on} | {sec:m1-taking-in} |
| Operationalization and scalability | Strata's risk tables showed {r:hindsight-caught} risks that completion reports later blamed. | {r:hindsight-caught\|measured_on} | {sec:m4-kpis} |
{when:measured:azure-spend} | Operationalization and scalability | Strata's Azure resources had cost {r:azure-spend}{r:azure-spend\|against}. | {r:azure-spend\|measured_on} | {sec:m4-costs} |
{when:unmeasured:azure-spend} | Operationalization and scalability | Strata has no Azure cost data yet. The daily cost pull adds each day's charges once Azure reports them. | Not measured yet | {sec:m4-costs} |

**Source:** Annex 1.

{#summary-designed} {when:designed} Some parts of Strata are designed but not built, and [the list after Module 4](#sec-designed-not-built) names each one.

{#summary-start} To see Strata work, open [the demo plan for P156634 in Check a plan]({url:app|/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09}), then [the project page for P130164]({url:app|/projects/P130164}).

## Where Strata earns each point {#rubric}

{#rubric-intro} The assessment scores the four dimensions. The table gives each criterion in the rubric's words, the paragraphs that answer it, and what you can open to see it working.

{rubric-map}

**Source:** the assessment's rubric ([docs/assessment.md](assessment.md#5-evaluation--assessment-rubric), section 5). Criteria are in the rubric's words, in sentence case. "Concrete metrics and KPIs" drops one word that Strata's writing rules leave out.

## Module 1: Ingestion and knowledge representation {#module-1}

Scored under [System and knowledge architecture](#rubric-architecture), and in part under [Domain alignment and data use](#rubric-domain).

{#m1-in-short} **In short.** Strata takes in {s:source-count} sources, fetches only what changed in each, and keeps every row with the date it became public. It joins records on their own keys first, and it reads long reports into numbered passages, each with its page. On the slice's documents, it read {r:pages-read-well} pages well.

### Taking in records and documents {#m1-taking-in}

{#m1-ask} The assessment asks for a pipeline that takes in tables and long documents and matches the same things across them. Strata names the assessment's layers of evidence What, How and Why, after the question each answers. [Annex 4](#sec-annex-words) maps the words.

{#m1-sources} The source registry, `config/sources.toml`, lists {s:source-count} sources. They hold the contract awards, the procurement notices, the projects, the loans and credits, the Independent Evaluation Group (IEG) ratings, the governance indicators and the project documents. Each entry names its endpoint, the field that marks new rows, how often Strata fetches it, its license and the transform that cleans it. Adding a source is one entry and one transform.

{figure:pipeline}
**Figure. Databricks holds the data, Foundry holds the agent, and the app runs every tool as the person asking.**
**Source:** the source registry and the tool registry, as this proposal was built.

{#m1-medallion} Each nightly run fetches only what changed. Bronze keeps each page as it arrived, silver holds typed and cleaned rows, and gold holds the knowledge model. Every row keeps the date the World Bank made it public, so Strata can answer as of any past day without using what came later (ADR 0002).

{#m1-contacts} Procurement notices name contact people, emails and phone numbers. Ingestion removes them before bronze keeps a page. It removed contact details from {r:contacts-removed} notices, and on {r:contacts-left|on} the nightly check found {r:contacts-left} notices with an email or phone number left.

{#m1-keys} Strata joins records on their own keys before it tries names. The STEP reference joins a notice, a contract and a Procurement Plan row. {r:linked-notice} contract award rows since fiscal 2020 carried a STEP reference that a notice also carried. For suppliers, the STEP supplier ID comes first. For {r:supplier-ids} awarded bidders whose award rows gave the same name, the rows also gave the same ID. Strata never merges different IDs on a name alone, and a person decides each uncertain match.

{#m1-gap} The awards datasets leave a gap. The older one covers fiscal 2001 to 2016 and holds only contracts under prior review. The newer one starts in fiscal 2020. Strata read the award notices for the years between and built {r:gap-contracts} contracts from them, each in the currency the notice gives. {fig:award-gap} shows the rows by year.

{figure:award-gap}
**Figure. The awards datasets hold no contracts for fiscal 2017 to 2019, so Strata built {r:gap-contracts} contracts from those years' award notices.**
**Source:** Strata's data readiness measures, the same measure as the dashboard's rows per fiscal year.

### The knowledge model {#m1-knowledge-model}

{#m1-model-ask} The assessment asks for a schema that matches records across keys that do not line up, such as a supplier's contract and a lesson in a completion report. Strata keeps that schema as tables in Unity Catalog, with an edge table between them (ADR 0004).

{#m1-model-edges} A shared key, such as the project ID or the STEP reference, joins records exactly. A scored link joins a contract to a report paragraph that names the contract, its place or its kind of work. The link's score also counts how close the report's date is to the signing. Strata calls that second kind "appeared together" and never says one caused the other. The link scorer kept {r:passages-linked} such pairs.

{figure:knowledge-model}
**Figure. Records and documents meet at the passage, joined on the project ID and the STEP reference.**
**Note:** {copy:trailLegend}

{#m1-model-trail} The assessment's own example is in P130164. Award notice OP00044090 records contract IN-RRSMP-7431-CW-RFB, signed on June 15, 2017, in a year neither awards dataset covers. The notice carries the package's STEP reference, so Strata joins it to the package on that key. The completion report's paragraph {r:trail|paragraph}, on page {r:trail|page}, appeared together with the contract. [Its contract trail]({url:app|/projects/P130164/packages/IN-RRSMP-7431-CW-RFB}) shows the award notice with its bids, the contract, and each report paragraph that appeared together with it.

{#m1-model-assertions} Reports also make dated claims, such as an ISR's rating of progress or a completion report's view of the same period. Strata keeps each one as an assertion with its source, its date and the period it is about. When assertions about the same thing differ, Strata records a disagreement. Module 3 explains how it handles one.

{#m1-model-neo4j} The tables answer every question Strata asks with joins of a few hops, and the agent's tools never need a path search. If paths grew well past the hop limit that ADR 0004 names, Neo4j would be the production option, loaded from the same edge table.

### Reading long reports {#m1-long-reports}

{#m1-reading-ask} The assessment asks how Strata reads long reports, with tables, annexes and technical text. Strata picks how to read each page and keeps the report's own paragraph numbers.

{#m1-reading-router} The page router chooses how to read each page. Where the World Bank publishes the page's text, Strata reads it. Where it does not, as with a scanned page, the layout parser reads the page's words and their boxes. Strata read {r:pages-published-text} pages from the published text, and {r:pages-read-well} pages well across both routes, in {r:documents-read} documents.

{figure:reading}
**Figure. A long report becomes numbered passages, each with its page.**
**Source:** the passage reader, `src/strata/reader`, and the model file, `config/models.toml`.

{#m1-reading-passages} Strata divides each report at its numbered paragraphs, as completion reports and appraisal documents number them. A table becomes one passage per row, with its header kept. Each passage keeps its page, its section and a header such as "ICR, P130164, India, roads, III.B, ¶54, p.23" that names where it came from. The knowledge model holds {r:passages} passages.

{#m1-reading-index} Strata embeds each passage with {model:embed}, as {s:embedding-size} numbers. The passage index is hybrid. It searches by words and by meaning, and it returns only passages public before the question's date.

{#m1-reading-shelf} Strata keeps a shelf of the hardest documents in the slice: a scanned appraisal document with a risk annex set in columns, the longest appraisal document, a Procurement Plan with hundreds of rows, a completion report in French and a document longer than the layout parser takes. The reader read {r:shelf-read} of them, and the Data readiness page records each outcome.

**What you can open.** [Data readiness]({url:app|/data}), [Sources and licenses]({url:app|/data/sources}), [the P130164 completion report at paragraph 54]({url:app|/projects/P130164/documents/icr-2019-10-10?page=23&para=54}) and [the source registry](../config/sources.toml).

## Module 2: Estimates and agentic retrieval {#module-2}

Scored under [Analytical and AI methodology](#rubric-method), and in part under [Domain alignment and data use](#rubric-domain).

{#m2-in-short} **In short.** Strata gives a time estimate with a range only when enough comparable packages back it, and it tests every range against what happened later. In the backtest, {r:backtest-coverage} test packages were signed within the 8-in-10 point of their range. Its agent picks tools, and the app runs them as the person asking.

### Time estimates and risk {#m2-time-estimates}

{#m2-ask} The assessment asks for a model that estimates how long a tender takes and how likely it is to change or be advertised again. Strata answers with a past range from comparable packages and a time estimate for the package itself.

{#m2-past-range} The past range is what happened to comparable packages: same category, method, market approach and size band. It counts packages still open, so a slow package is never dropped for being slow. Strata gives no range from fewer than {s:fewest-comparables} comparable packages. Below that, it shows the packages one by one and says why.

{#m2-estimate} The time estimate comes from a survival model trained on past packages. It gives the middle and the 8-in-10 point. Each year from 2021 to 2025, a backtest trained the model only on what was public by January 1 and scored it on packages advertised that year. Across the test years, {r:backtest-coverage} test packages were signed within the 8-in-10 point. A track record under every estimate shows how earlier estimates for packages like it turned out.

{figure:backtest}
**Figure. Across the test years, {r:backtest-coverage} packages were signed within the 8-in-10 point of their range.**
**Source:** the time estimate's rolling backtest, in `strata.ops.evaluation_result`.
**Note:** A year with too few packages for a percentage shows its count and no dot.

{#m2-signals} Strata also checks each package in a plan for reasons to look: a planned date already past, a closing date moved, a direct selection made late. A signal is a reason to look, never a finding. A backtest compared an early-warning model with these fixed checks on projects that later extended their closing date. The model caught {r:hazard-caught} such projects, and the fixed checks caught {r:signals-caught}.

{#m2-rebidding} Strata labels rebidding risk Experimental. It counts the comparable packages that were advertised again and why, and it gives a model's frequency only when the model beat its baseline in its backtest.

{#m2-modifications} Contract modifications are harder. The public records hold each contract's signed amount but rarely say why a contract changed later. Strata shows what the records hold and says what they leave out. Governance indicators enter the model only as they were published at the time.

### Agentic retrieval {#m2-retrieval}

{#m2-retrieval-ask} The assessment asks for retrieval that finds comparable packages, specifications like the new one and past lessons when someone starts a package. In Strata, the agent decides which tools to call, and the app runs each one as the person asking (ADR 0003).

{#m2-retrieval-tools} The tools reach SQL over the records, through Genie for questions in words, the hybrid passage index and the knowledge model's edges. Each tool returns rows or passages with an id, the date each became public and a coverage line. The agent gets at most {s:tool-rounds} rounds of tool results for one answer. What the tools return is the evidence pack, and an answer can cite only what is in it.

{figure:retrieval}
**Figure. One answer: the agent picks the tools, the app runs them as the person asking, and the verifier checks every sentence.**
**Source:** the agent's tool registry, `config/tools.toml`, and ADR 0003.

{#m2-retrieval-measured} The retrieval evaluation asks questions whose right passages are known and uses only documents public before each question's date. In the newest run, on the ICR Review citation set, precision at 10 was {r:retrieval-precision}, recall at 20 was {r:retrieval-recall} and nDCG at 10 was {r:retrieval-ndcg}.

### What a specialist gets at each stage {#m2-stages}

{#m2-stages-intro} The assessment names the stages of procurement. The table says what Strata does at each one and where to see it.

**What Strata does at each procurement stage.**

| Stage | What Strata does | Where in Strata |
|---|---|---|
| Planning and strategy | Checks each row of a Procurement Plan against comparable packages, and gives a planned date for each STEP step. | [Check a plan]({url:app\|/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09}) |
| Tender design and packaging | Shows the market approach and method that comparable packages went with, and checks qualification criteria against theirs. | [A package workspace]({url:app\|/packages/KE-NWWDA-541055-CW-RFB}) |
| Execution and monitoring | Follows projects and shows signals, each a reason to look, with the records behind it. | [Following]({url:app\|/projects/following}) |
| Continuous learning | Proposes lessons from new completion reports, quoted word for word with their page, for a person to decide. | [Lessons]({url:app\|/lessons}) |

{#m2-drafts} Strata also writes drafts: review notes, a mission brief and suggested rows for the borrower's PPSD. Each looks like the document it becomes. A person moves it from Draft to Checked by you to Exported, and exporting sends nothing to anyone.

**What you can open.** [A package workspace with its time estimate]({url:app|/packages/KE-NWWDA-541055-CW-RFB}), [the one box on the P130164 project page]({url:app|/projects/P130164}) and [the AI quality and adoption page]({url:dashboard}).

## Module 3: Guardrails, faithfulness and attribution {#module-3}

Scored under [Analytical and AI methodology](#rubric-method).

{#m3-in-short} **In short.** Strata states only numbers a tool returned, and every sentence must cite what backs it. The verifier runs {s:check-count} checks on every sentence and removes any sentence that fails, with its reason. In the latest full gate, {r:benchmark-passed} benchmark questions passed.

### Checks before anyone sees an answer {#m3-checks}

{#m3-checks-ask} The assessment asks for concrete layers of checks that keep every recommendation tied to documents and records. Strata's verifier runs on every answer and every draft, and nothing skips it.

{#m3-checks-list} A number or date must match a row the sentence cites, at the same rounding. Every id a sentence cites must have come back from a tool in that answer. A quote must be word for word on its page. A model then judges whether each sentence follows from its sources. Advice must cite a lesson or a comparable package. A sentence that rests on one side of a disagreement shows both sides.

{figure:checks}
**Figure. Every sentence passes the verifier's checks before anyone sees it.**
**Source:** the verifier, `src/strata/agent/verifier.py`.

{#m3-checks-data} Documents are data, never instructions. Prompt Shields scanned every passage when Strata read it, and the agent's instructions keep rules apart from the text it reads.

{#m3-checks-line} Under each answer, a check line says what Strata checked against records and pages, what a model judged, and what nobody checked. A removed box lists each sentence the verifier took out and why. Over the period the pull covered, the verifier removed {r:sentences-removed} sentences, and Strata held back in {r:answers-held-back} answers.

{#m3-refusals} Strata turns down {s:refusal-count} kinds of request every time, such as scoring suppliers or commenting on a tender still open. Each refusal is tested as one. In the latest full gate, Strata turned down {r:must-refuse} must-refuse questions. Foundry's groundedness evaluator rated {r:groundedness} answers as grounded in their sources.

### When reports disagree {#m3-disagree}

{#m3-disagree-ask} The assessment asks how to settle evidence that disagrees, such as a completion report that differs from mid-term supervision ratings. Strata keeps both sides and says which one it leans on, and by which rule. It found {r:disagreements} disagreements.

{#m3-ladder-intro} The evidence ladder, `config/evidence_ladder.toml`, decides which side Strata leans on. The first rule that applies decides:

{ladder}

{#m3-showcase} The assessment's own case is in P130164. [ISR 7]({url:app|/projects/P130164/documents/isr-07-2016-08-26?page=1}), archived on August 26, 2016, after the mid-term review, rated progress towards the development objective "Satisfactory". The completion report's paragraph 78, on page 27, says: "Indeed, it was clearly identified at the MTR that the achievement of part of the PDO was compromised by the major delays in implementing activities under Components 2 and 3 and lack of endorsement from relevant stakeholders." ([ICR, P130164, paragraph 78, page 27]({url:app|/projects/P130164/documents/icr-2019-10-10?page=27&para=78})) For a judgment of how a project went, Strata leans on the later, more independent report, so it leans on the completion report and keeps ISR 7 as the record of the earlier view.

{#m3-card} A disagreement card shows both sides in the order they were written, the side Strata leans on, the rule that decided it, and what would change if you kept the other. Keeping the other side needs a reason, and Strata records it.

**What you can open.** [The check line and the removed box under an answer on the P130164 project page]({url:app|/projects/P130164}), [the P130164 timeline]({url:app|/projects/P130164/timeline}) and [the benchmark file](../evals/benchmark.yaml).

## Module 4: Learning loops and implementation {#module-4}

Scored under [Operationalization and scalability](#rubric-operations).

{#m4-in-short} **In short.** Strata learns through {s:loop-count} loops that share one dated store, and each loop changes Strata only after a gate. Its risk tables showed {r:hindsight-caught} risks that completion reports later blamed. Rollout would widen only when each phase meets its targets.

### Learning loops, one dated store {#m4-loops}

{#m4-loops-ask} The assessment asks for a feedback loop in which new milestones, supervision notes and contract changes update the models and the passage index. Strata runs a loop each for knowledge, retrieval and estimates, and each writes what it changed, and when, to `strata.ops`.

| | Knowledge | Retrieval | Estimates |
|---|---|---|---|
| Trigger | A new ICR, ICR Review or PPAR | A report on a passage, with a reason; new passages | Signings and plan dates; drift |
| Cadence | Taken in nightly; decided within {s:lesson-decision-days} business days | Labels weekly; search tuned at most monthly | Watched monthly; retrained quarterly |
| Owner | A regional lead procurement specialist | The search owner, with specialists judging labels | The model owner, with the lead's sign-off |
| Gate | The quote is word for word on its page; a lead decides | No loss on the held-out set or the hindsight test | Wins its backtest and a quarter in shadow; coverage holds for each edition of the Regulations |

{figure:loops}
**Figure. The knowledge, retrieval and estimates loops share one dated store.**
**Source:** Strata's loops, as `strata.ops` records them.

{#m4-governance} Strata proposes lessons, and people decide. An accredited procurement specialist recommends a lesson, and a lead procurement specialist decides it. IEG stays independent, and its ICR Reviews are evidence at the top of the ladder. A report from a person about a passage becomes a label for a person to check, never production data, until a reviewer decides it.

{#m4-exposure} Strata logs every range it shows. A later plan date set within days of Strata's value counts as anchored, so plan accuracy is reported apart for plans that used Strata and plans that did not. Projects exposed to Strata stay out of the hindsight test.

### Key performance indicators {#m4-kpis}

{#m4-kpis-intro} The table follows the results framework of a World Bank project. Each indicator is defined once, in the KPI registry, `config/kpis.toml`, and the dashboard reads the same definition. The names and definitions are the dashboard's own words, quoted.

**The indicators Strata reports, and where each one stands.**

{framework}

**Source:** the KPI registry and Annex 1.

{#m4-pilot} Weekly users, plans dated near Strata's ranges and procurement planning cycle time need people using Strata for their work. During the build, only test accounts used it, so these indicators have no meaningful value yet. The pilot measures them against countries not yet onboarded.

{#m4-hindsight} The hindsight test replays Strata as of each closed project's approval date and asks whether its risk tables would have shown the risks the completion report later blamed. Strata's tables showed {r:hindsight-caught} blamed risks. A checklist of each sector's commonest risks named {r:hindsight-checklist}.

{figure:hindsight}
**Figure. Strata's risk tables showed {r:hindsight-caught} risks that completion reports later blamed, and a sector checklist named {r:hindsight-checklist}.**
**Source:** the hindsight test, in `strata.ops.evaluation_result`.

### A phased rollout {#m4-rollout}

{#m4-rollout-intro} Strata would reach more people only when the phase before meets its targets. Phases start on those gates, not on dates.

**Strata reaches more people only when the previous phase meets its gates.**

| Phase | Who uses Strata | What they get | Starts when |
|---|---|---|---|
| Phase 1 | World Bank procurement specialists and task team leaders in {s:pilot-countries} countries | Everything in the World Bank staff view | The backtest's coverage stays in its band, the full gate passes and the demo-ready command passes |
| Phase 2 | Implementing agencies in those countries | The implementing agency view, private uploads and drafts | Phase 1's indicators in the results framework meet their targets |
| Phase 3 | The public | A read-only view | Phase 2's indicators meet their targets, and a review of what the public view shows |

{#m4-later} Some parts could come later: debarment checks through an official interface, with a person confirming every match; a Teams channel; a public site for contract trails; a Word add-in for the PPSD; and the interface in French, Spanish and Portuguese.

### Cost caps and actual spend {#m4-costs}

{#m4-spend} {when:measured:azure-spend} By {r:azure-spend|latest}, the latest day with cost data, Strata's Azure resources had cost {r:azure-spend}{r:azure-spend|against} for {r:azure-spend|period}. Azure budgets only send alerts, so hard caps limit spend.

{#m4-spend} {when:unmeasured:azure-spend} Strata has no Azure cost data yet. The daily cost pull adds each day's charges once Azure reports them. Azure budgets only send alerts, so hard caps limit spend.

**Hard caps hold Azure spend, because Azure budgets only send alerts.**

{caps}

**Source:** Annex 2. Each cap was read back from Azure where Annex 2 says so.

### Changing Strata in under ten minutes {#m4-drill}

{#m4-drill-intro} Each change the panel may ask for in round 2 lives in one place, a registry or a config file, so it can land in under ten minutes with the gate green. The change drill lists {s:drill-count} of them.

**Each change Strata expects in round 2 lives in one place.**

{drill}

{when:unrehearsed} **Note:** The rehearsal times come from the change drill run in phase P4. This version was built before it.

{when:rehearsed} **Source:** Annex 1. Each time ran from making the drill's own branch to the commit the gate passed on it, and no drill's change stayed in Strata. The steps of each drill are in [the change drill's runbook](change-drill.md).

**What you can open.** [The Governance page]({url:dashboard}), [Lessons]({url:app|/lessons}) and [the change drill's list](../config/change_drills.toml).

## Designed, not built {#designed-not-built}

{#designed-intro} {when:designed} These parts of Strata are designed, and this proposal describes them, but they are not in the app yet. Where the app would show one, it shows the label "Designed, not built" and says what it does instead.

{designed}

## Annex 1: Results register {#annex-results}

{annex:results}

## Annex 2: Settings and counts {#annex-settings}

{annex:settings}

## Annex 3: Data sources and licenses {#annex-sources}

{annex:sources}

## Annex 4: Words and abbreviations {#annex-words}

**The assessment's words, and Strata's.**

<table>
<thead><tr><th scope="col">The assessment says</th><th scope="col">Strata says</th></tr></thead>
<tbody>
<tr><td data-quote="assessment">Structured data</td><td><a href="../GLOSSARY.md#evidence">What</a></td></tr>
<tr><td data-quote="assessment">Semi-structured information</td><td><a href="../GLOSSARY.md#evidence">How</a></td></tr>
<tr><td data-quote="assessment">Unstructured knowledge</td><td><a href="../GLOSSARY.md#evidence">Why</a></td></tr>
<tr><td data-quote="assessment">chunk</td><td><a href="../GLOSSARY.md#evidence">passage</a></td></tr>
<tr><td data-quote="assessment">conflicting evidence</td><td><a href="../GLOSSARY.md#evidence">disagreement</a></td></tr>
<tr><td data-quote="assessment">re-bidding</td><td><a href="../GLOSSARY.md#procurement">rebidding</a></td></tr>
<tr><td data-quote="assessment">precedent</td><td><a href="../GLOSSARY.md#analysis">comparable</a></td></tr>
<tr><td data-quote="assessment">timeline benchmarking</td><td><a href="../GLOSSARY.md#analysis">past range and time estimate</a></td></tr>
</tbody>
</table>

ADR, Architecture Decision Record. CPIA, Country Policy and Institutional Assessment. ICR, Implementation Completion and Results Report. IEG, Independent Evaluation Group. ISR, Implementation Status and Results Report. KPI, key performance indicator. MTR, mid-term review. nDCG, normalized discounted cumulative gain. PAD, Project Appraisal Document. PDO, project development objective. PPAR, Project Performance Assessment Report. PPSD, Project Procurement Strategy for Development. STEP, Systematic Tracking of Exchanges in Procurement. WGI, Worldwide Governance Indicators.

{copy:footer}
