# 36: Suggested PPSD risk rows and the Project Paper summary, exported to Word

**What to build:** From the risks selected on the package workspace, a World Bank specialist gets suggested risk rows for the borrower's PPSD in the template's own columns, and, separately, a draft procurement summary for the Project Paper. The workspace's sticky action "Suggest N PPSD risk rows" starts the suggest-PPSD-rows workflow, whose writer fills Risk Description and Description of mitigation with counts and sources as footnotes. The Short Form (Risk Description, Description of mitigation, Risk Owner) is the default; the Long Form toggle appears only when a contract crosses the PPSD guidance's Table I thresholds from the thresholds file, adding Likelihood and Impact (1 to 5), the Overall Risk Score and the Procurement Process Stage, all left for people to fill. Strata never fills risk owners, ratings, references or actual dates; "Set the owner" sits in each empty owner cell and the page counts "N of 3 risk owners set". Export to Word is held only where the person commits: every owner set (and every rating, in the Long Form) and every disagreement on the draft resolved, with the reason shown when held. The Project Paper procurement summary is drafted from the plan check, the implementing agency's track record (how its past packages went against its plans) and any PPSD rows, with the same states, bar and exports.

Read first: docs/PLAN.md section 6 (Formats); the blueprint's Draft wireframe, Package workspace wireframe (the sticky action and section 3) and "Where Strata enters the work" ("Formats Strata writes in"); DESIGN.md sections 5 and 7; docs/agents/areas/agent.md.

**Blocked by:** 30 (Procurement risks and what helped, on the package workspace); 35 (Drafts: the runtime, the draft bar and review notes on a plan)

**Status:** ready-for-agent
**Area:** agent
**Phase:** P2
**Design review:** yes

- [ ] Three selected risks produce a draft whose rows read like the Draft wireframe's, with footnotes such as "Seen in N of M comparable completion reports" and "ICR P130164 ¶54, page 23; ICR Review 10.b", every count taken from a tool.
- [ ] The Short Form shows exactly Risk Description, Description of mitigation and Risk Owner; the Long Form toggle appears only for a package above the Table I threshold in the thresholds file and adds its four columns, empty.
- [ ] A test proves Strata never writes a risk owner, rating, reference or actual date.
- [ ] The owner count updates as owners are set; export is held until every owner is set and every disagreement is resolved, and the bar says why.
- [ ] The exported Word file's table has the template's column headers, and its footnotes match the draft's.
- [ ] The Project Paper summary for P156634 cites the plan check's counts and the agency's track record with numbers from tools, and passes the six checks.
- [ ] Both drafts follow the Draft wireframe and DESIGN.md sections 5 (Draft bar) and 7 (no rule 19 words; "suggested rows for the borrower's PPSD"); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
