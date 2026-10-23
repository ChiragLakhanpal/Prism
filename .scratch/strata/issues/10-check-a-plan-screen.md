# 10: Check a plan, on screen, for the NWWDA plan

**What to build:** A World Bank procurement specialist opens P156634, goes to Procurement, picks the Northern Water Works Development Agency's October 9, 2026 plan, and sees every activity checked, as the blueprint's Check a plan wireframe draws it. This ticket adds a minimal project page (a header with the project name, the P-code in mono, the country, the status and the implementing agency, and a tab row showing only the tabs that are built, here Procurement); the Procurement tab, listing each implementing agency's plans with their dates; and the Check a plan page: the breadcrumb, a sticky header with the "8 activities checked" pill, a summary sentence whose counts match the rows, the table in STEP's columns (Activity, Method · market approach, Review, Estimated (US$), Process status, What Strata found), marks as status badges with past-tense reasons, packages with no signals folded behind "Show them", the note on what Strata cannot see, and a source line. The Projects tab gets a minimal All projects list whose P-codes link to their project pages. The primary action "Draft review notes" arrives with the drafts ticket.

Read first: DESIGN.md sections 5, 7 and 10; the blueprint's Check a plan wireframe and its three "why" panels, and the "Words" section; docs/agents/areas/app.md.

**Blocked by:** 06 (The app shell, deployed as a Databricks App that acts as the viewer); 09 (The tool registry with the as-of contract, and check_plan)

**Status:** ready-for-agent
**Area:** app
**Phase:** P1
**Design review:** yes

- [ ] Against the mocked API, Playwright finds the eight activities and the summary "One needs a look and two are worth watching; three have data notes", with two packages folded behind "Show them", which opens them by mouse and keyboard.
- [ ] Reasons are built from copy-file templates filled with tool values and read as the wireframe does, for example "Planned completion July 31, 2026 passed with no signed contract. The project closes October 31, 2026."
- [ ] Column names and values are STEP's, word for word ("Request for Bids · Open - National", "Post", "Pending Implementation"), as DESIGN.md section 7 rule 17 requires.
- [ ] The table follows DESIGN.md section 5 (title sentence, count line, header in surface-2, units in column heads, numbers right-aligned with tabular numerals, source line below) and STEP references are set in Roboto Mono.
- [ ] Marks use the status badge from DESIGN.md section 5 with icon and text; Data note uses the neutral state; nothing relies on color alone.
- [ ] The note "Not visible to Strata: the prior-review queue, complaints, contract amendments and contract management reports. Those stay in STEP." appears as in the wireframe.
- [ ] Loading, empty (an agency with no plan) and error states exist and are captured at 1440, 1024 and 390 px; below 768 px the table becomes cards; axe finds no WCAG 2.2 AA violations.
- [ ] On the deployed app, a workspace user opens the NWWDA October 9, 2026 plan and sees the same counts: the first half of P1's exit criterion.
