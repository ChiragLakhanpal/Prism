# Strata

Strata is procurement intelligence for World Bank-financed projects. It links what happened in past procurements to the documents that explain how and why, so the people who plan, design, monitor and learn from procurement can see the evidence behind every answer.

## Language

### Evidence

**Stratum**:
One of the three layers of evidence Strata links, named for the question it answers: What, How or Why.
_Avoid_: Tier, evidence layer, source type

**What**:
The stratum of records of what happened, such as contract awards, notices, project data, disbursements and governance indicators.
_Avoid_: Structured data (in user-facing copy)

**How**:
The stratum of operational documents on how procurement was carried out, such as procurement plans and ISRs.
_Avoid_: Semi-structured data (in user-facing copy)

**Why**:
The stratum of narrative documents that explain design choices and outcomes, such as PADs, ICRs and ICR Reviews.
_Avoid_: Unstructured data (in user-facing copy)

**Passage**:
A numbered paragraph or table row in a document, and the unit every citation points to, together with its page.
_Avoid_: Chunk, snippet

**Published text**:
The text the World Bank publishes with a document, which Strata reads page by page into passages. Strata's code calls it Route A.
_Avoid_: Route A (in user-facing copy), OCR text

**Layout parser**:
The reader Strata sends a page to when the published text cannot be trusted with it: a scanned page, a table such as a Procurement Plan's or a PAD's risk table, or a figure. It reads the page's rows, columns and text. Strata's code calls it Route B.
_Avoid_: Route B (in user-facing copy), OCR

**Table summary**:
The one passage Strata writes about a table it read, which says what the table is and names its rows. It is Strata's own words, so it never backs a number; the table's rows do.
_Avoid_: Table description

**Stress shelf**:
The hardest documents Strata reads, each with a recorded outcome on the Data readiness page, which shows them as "The hardest documents I read".
_Avoid_: Stress shelf (in user-facing copy), benchmark documents

**Pilot projects**:
The water and transport projects in Kenya, Bangladesh, Vietnam and Pakistan with a Board date in fiscal 2012 to 2025, whose documents Strata reads, as `config/slice.toml` sets them. Strata's code calls them the slice.
_Avoid_: Slice (in user-facing copy), pilot slice

**Assertion**:
A dated claim a source makes about a project, package or contract, such as a rating, a date or an amount.
_Avoid_: Fact, statement

**Evidence tier**:
How independent and how retrospective a source is, which decides whose assertion Strata leans on when sources disagree.
_Avoid_: Source rank

**Disagreement**:
Two assertions about the same thing, for the same period, that cannot both be true. A rating that changes over time is a trajectory, not a disagreement.
_Avoid_: Conflict (reads as conflict of interest), contradiction, discrepancy

**Evidence pack**:
Everything an answer or a draft may cite. For an exported draft, the PDF and CSV that list those sources, where each is cited, and whether its author opened it.
_Avoid_: Context

**Data readiness**:
How fit a source is to support answers, measured by its coverage, how much of it links to projects, how well it was read, and how fresh it is.
_Avoid_: Readiness on its own (the World Bank uses it for projects and borrowers), data quality score

**Throttled**:
The outcome of a daily cost pull when Azure answered "too many requests" to every try and asked Strata to wait. The pull's run row in strata.ops.cost_pulls records it with Azure's message. The pull wrote no charge for that day, its job still succeeded, and the next day's pull tries again. The Governance page shows that day as a day with no charges, then says Azure throttled the cost pull.
_Avoid_: Failed (for a throttled pull)

**Working language**:
The language a person asks Strata to write answers and drafts in: English, French, Spanish or Portuguese. The screens stay in English, and sources keep their own language, word for word.
_Avoid_: Locale, interface language

**Mid-term review (MTR)**:
The review the World Bank and the borrower hold about halfway through a project, to check its progress and decide whether to change its design or its targets. A report that writes "MTR" means this review.

### Procurement

**Package**:
One planned procurement with its own reference number in a procurement plan, and the thing a user plans or checks. It is always shown with its STEP activity reference; STEP calls it an activity, and people also say contract package or tender.
_Avoid_: Purchase requisition (PR), purchase order (PO), a selection method's name used for the package itself

**Lot**:
A part of a package that is evaluated and awarded as its own contract.
_Avoid_: Slice (the Procedure's synonym, accepted on input)

**Contract**:
A signed award to a supplier. One package can produce several.

**Selection method**:
How a package goes to market under the Procurement Regulations: Request for Bids (RFB), Request for Quotations (RFQ), Request for Proposals (RFP), Direct Selection, or a consultant method such as QCBS.
_Avoid_: ICB, NCB, Shopping, Direct Contracting (old names, accepted on input)

**Market approach**:
Whether a package is advertised openly or to a limited list, and nationally or internationally.
_Avoid_: Market on its own

**Implementing agency**:
The borrower's entity that carries out procurement for a project, called a PIU, PMU or PCU locally.
_Avoid_: Client, PIU (in copy shared across countries)

**Procurement cycle time**:
The time from a package's specific procurement notice to its signed contract.
_Avoid_: Time to award (award comes before signature)

**Delay**:
The gap between a date in the procurement plan, as first published, and the date the step actually happened.
_Avoid_: Slippage

**Baseline**:
The version of an implementing agency's Procurement Plan that World Bank staff saved as the plan agreed at negotiations. Later checks of that agency's plans also give the delay from the baseline's planned dates, beside the delay from the first published planned date; the baseline never changes a signal.
_Avoid_: Original plan (the first published version is a different thing)

**Upload**:
A Procurement Plan an implementing agency team gave Strata to check. It is Official Use Only, and only that team sees it.
_Avoid_: Submission

**STEP row**:
One activity in STEP's own columns, with the planned dates filled by Strata and the references, actual dates and ratings left to people and STEP.
_Avoid_: STEP line, export row

**Rebidding**:
Inviting bids again after a procurement process was canceled or all bids were rejected.
_Avoid_: Re-bid, re-tender

**Qualification criteria**:
The requirements a bidding document sets for bidders, such as similar experience, average annual turnover, equipment and key staff. Strata compares them item by item with comparable packages whose notices published theirs.
_Avoid_: Criteria on its own (it means how comparable packages are chosen)

**Cost estimate**:
The amount a Procurement Plan gives a package before it goes to market, STEP's Estimated Amount (US$).
_Avoid_: Estimate on its own (it reads as a time estimate)

**Loan number**:
The number of one part of a project's financing, as the project's record in the projects API names it: an IBRD loan (IBRD-8956), an IDA credit (IDA-60300), an IDA grant (IDA-H8060), a trust fund (TF-C3892) or co-financing (COFN-00280). Strata keeps every number a project's record names, each with its financier, the letters before the number. A loan or credit is stored as its lender and digits (IDA60300). Any other number keeps its letter after one hyphen (IDA-H8060), so a grant never reads as a credit. A project's loan numbers include its grants and trust funds. The IDA dataset lists grants beside credits, so its counts on the Data readiness page include grants too. A notice that writes only digits (60300) is matched to a loan or credit, never to a grant.

### Analysis

**Comparable**:
A past package or project chosen by stated criteria (method, category, market approach, review type, size band, region and period) to inform a new one.
_Avoid_: Similar package, precedent

**Past range**:
The range of actual outcomes across a set of comparables.
_Avoid_: Benchmark (the World Bank uses it for prices), norm, average

**Time estimate**:
Strata's calibrated range for how long one specific package will take.
_Avoid_: Estimate on its own (reads as a cost estimate), prediction, forecast

**Lesson**:
A finding from an evaluation document about what helped or hurt, kept with its verbatim quote and page, that a lead procurement specialist has decided belongs in the library.
_Avoid_: Insight, learning

**Proposed lesson**:
A lesson Strata extracted that no person has decided on yet. Only reviewers see it.
_Avoid_: Draft lesson, candidate (in user-facing copy)

**Lesson version**:
One numbered state of a lesson. Drafts cite a lesson at a version, so nothing in a draft changes without its author.

**Lesson reviewer**:
An accredited or lead procurement specialist the roles file names for one or more regions. An accredited specialist recommends; a different lead decides, and nobody acts on their own project.
_Avoid_: Approver, moderator, editor

**Re-check**:
A second review of a lesson already in the library, which ends with the lesson kept, changed or retired. Any lesson reviewer can ask for one, with a reason.
_Avoid_: Appeal, revision request, undo

**Cross-check**:
A sample of each quarter's lesson decisions, read by reviewers in another region, who agree or disagree. A disagreement starts a re-check where the lesson was decided.
_Avoid_: Audit, second review, spot check (in user-facing copy)

**Passage report**:
A person's mark that a passage was the wrong one, or not useful, for the question they asked, sent from the evidence drawer with an optional reason. It changes nothing in how Strata ranks passages until a passage reviewer decides.
_Avoid_: Flag, feedback flag

**Passage reviewer**:
A person the roles file names to decide whether a passage people reported is ranked lower for a kind of question. A passage reviewer never decides on a report they sent.
_Avoid_: Moderator, approver

**Audit sample**:
At scale, one in ten of the passages Strata ranked lower on its own, because several people made the same passage report and nobody disagreed, sent to a passage reviewer to leave it ranked lower or restore its ranking. It checks Strata's own decisions on passage reports; a cross-check is about lesson decisions, read in another region.
_Avoid_: Spot check, audit (alone), cross-check (for passages)

**Query judge**:
One of two people who grade, each on their own, the passages pooled for a query in the labeled set Strata measures search on.
_Avoid_: Rater, annotator (in user-facing copy)

**Edition (of the procurement rules)**:
The version of the World Bank's procurement rules a project followed, such as the January 2011 Guidelines or a numbered edition of the Procurement Regulations, read from its appraisal document.
_Avoid_: Policy version, ruleset

**Signal**:
A fixed check on public records that gives a reason to look, never a finding.
_Avoid_: Flag, red flag (an integrity term), alert, risk score

**Hindsight test**:
Replaying Strata as of a closed project's approval date to count which risks later blamed in its completion report Strata would have shown.

**Hindsight recall**:
Of the risks completion reports later blamed, the share Strata would have shown in the top five for their package on the project's approval date: coverage (a lesson covered the risk at approval) times shown-when-covered. The hindsight test reports it, and projects exposed to Strata are left out.

**Leading indicator**:
A loop's measure that moves first, as soon as people use what the loop changed, such as days from publication to decision for lessons.

**Lagging indicator**:
A loop's measure that confirms a leading indicator later, once outcomes are known, such as hindsight recall for lessons or plan accuracy for time estimates.

**Anchored plan row**:
A plan row published after Strata showed a past range or time estimate for its package, whose planned signing date fell within 14 days of a date Strata offered. Screens write "plan rows dated within 14 days of a date I offered".
_Avoid_: Anchored (in user-facing copy)
