# 22: Edges between strata: the contract trail and the Connections tab

**What to build:** Contracts, notices, packages, suppliers and passages are linked in one edge table, and people see those links as an activity's contract trail and as a project's Connections tab. The link scorer pairs each contract with passages from its project and scores the pair on project, sector, time proximity, text similarity and shared mentions (STEP references, contract names, places), keeping pairs above a threshold from the thresholds file with their score components; every such link is shown as "appeared together", never as cause. The activity page, under its project by STEP reference, traces plan row, notice, bids (bidders, prices and rejection reasons from award notices; individual consultants unnamed), contract, and the passages that appeared together with it, each with a source line. In the evidence drawer, "Why this source" explains a link in words from its score components. The Connections tab draws the project's one-hop neighbourhood, at most about 20 nodes with the rest counted by kind, and becomes a list below 768 px. "Open the activity" links on plan rows now land on the activity page. Edges respect the as-of date.

Read first: docs/PLAN.md section 5 (Links); ADR 0004; the blueprint's "Records and documents meet at the passage", Evidence drawer wireframe and "Navigation and roles"; DESIGN.md sections 5, 6 and 10.

**Blocked by:** 19 (Suppliers resolved on STEP IDs first, names second); 21 (The project page as the hub)

**Status:** ready-for-agent
**Area:** knowledge
**Phase:** P2
**Design review:** yes

- [ ] An edge links contract IN-RRSMP-7431-CW-RFB (signed June 15, 2017) to ICR P130164 ¶54 with its score components, and the drawer's "Why this source" reads like the Evidence drawer wireframe's note ("works contracts, roads, a closed project; linked to award notice IN-RRSMP-7431-CW-RFB, signed June 15, 2017").
- [ ] A four-hop path (supplier, contract, project, completion-report passage) is answered by recursive SQL over the edge table in a test.
- [ ] The activity page for KE-NWWDA-229129-CW-RFB shows the plan row (estimate US$300,000), the notice, the bidders from the award notice and the contract (signed January 3, 2022, US$1,245,092.76), each with a source line.
- [ ] No supplier score, rank or profile appears on the activity page, and individual consultants are not named.
- [ ] The copy for links says "appeared together" and the copy lint finds no causal wording on these screens.
- [ ] Connections draws at most 20 nodes and summarizes the rest as "and N more" by kind; every node is reachable by keyboard and opens its page or the drawer; below 768 px it is a list.
- [ ] As of a date before a contract was signed, its edges are not returned.
- [ ] Both screens follow DESIGN.md sections 5 and 10, are captured at 1440, 1024 and 390 px in loading, empty, error and populated states, and pass axe.
