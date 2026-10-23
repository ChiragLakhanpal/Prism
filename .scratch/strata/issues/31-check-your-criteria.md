# 31: Tender design: check your criteria and the cost estimate

**What to build:** Before a package is advertised, a specialist pastes its qualification criteria and sees how comparable packages set theirs, how often bids were rejected and why, and whether the cost estimate sits where comparable contracts were signed: section 5 of the package workspace, optional and collapsed by default. A check-your-criteria workflow (Microsoft Agent Framework, in code) breaks the pasted text into items (experience, turnover, equipment, key staff and the like), searches the notice passages of comparable packages whose criteria are public, and compares item by item with counts. It adds rejection reasons quoted from comparable award notices, the cost estimate against the signed amounts of comparable packages (abstaining below 20), and lessons on cost estimates and specifications from get_lessons. Everything passes the six checks. A request to judge the bids or evaluation of a live tender is refused in the first person.

Read first: docs/assessment.md (Tender Design and Packaging); the blueprint's "Who reaches for Strata, and when" (the tender design row) and Package workspace wireframe (section 5); DESIGN.md sections 5 and 7; docs/agents/areas/agent.md.

**Blocked by:** 15 (Plan a package from a sentence); 18 (The document slice, the page router's Route B and the stress shelf); 29 (The knowledge loop: proposed lessons with verified quotes, the review queue and versions)

**Status:** ready-for-agent
**Area:** agent
**Phase:** P2
**Design review:** yes

- [ ] With the scripted agent on the fixture, pasted criteria asking for similar experience of two contracts of US$10 million produce a comparison stating how many comparable notices with public criteria asked for the same or less, each count matching the tool's rows and citing notice passages.
- [ ] Rejection reasons appear as "N of M comparable packages had bids rejected", each reason quoted from an award notice with its notice id.
- [ ] The cost estimate is compared with the signed amounts of comparable packages, and with fewer than 20 the section abstains in the first person and lists them.
- [ ] Lessons on cost estimates appear with their citations, including ICR P130164 ¶54.
- [ ] A request to judge a specific live tender's bids is refused in the first person from the copy file.
- [ ] Collapsed, the section reads "optional. Paste your qualification criteria to compare them with N packages whose criteria are public." with N from the tool, under the eyebrow "Tender design", as in the Package workspace wireframe.
- [ ] States are captured at 1440, 1024 and 390 px, follow DESIGN.md sections 5 and 7, and pass axe.
