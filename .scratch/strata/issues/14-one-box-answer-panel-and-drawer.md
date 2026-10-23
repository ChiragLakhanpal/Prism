# 14: Ask from the one box: the answer panel and the evidence drawer

**What to build:** From the one box on any page, a person types and sees what Enter will do before pressing it; choosing "Ask this" streams a cited answer into an answer panel under the band; and any citation opens the evidence drawer beside the page, never over it. The box: "/" focuses it; as you type it lists actions from one set of intent rules that later tickets extend (a P-code offers "Open"; a loan number in any of its four forms opens its project; a STEP reference opens its project's plan check with the row in view; anything else offers "Ask this"). On a project or package page it carries a removable scope chip. The answer panel shows steps as they happen, then "In short" with citation markers, the neutral check line, and the removed box open by default with the first removed sentence and its reason. A marker's hover or focus shows the evidence card; a click opens the drawer at that passage: the whole numbered paragraph with the matching words highlighted, its meta line, a switcher for the claim's other sources, "Open at page N" (to the World Bank's PDF at that page until the in-app source view exists), a 44px close, Escape to close and focus returned to the marker. The drawer's state lives in the URL's evidence parameter, so a link reopens it, and below 768 px it becomes a full-screen sheet. Citations a person opens show a visited state and are recorded per viewer in strata.ops, for "You opened 3 of 14 sources" later.

Read first: DESIGN.md sections 5 (Citation marker, Evidence card, Evidence drawer, Check line, Removed box) and 10; the blueprint's Package workspace wireframe ("In short"), Evidence drawer wireframe and "Navigation and roles" ("One box, the same place"); docs/agents/areas/app.md.

**Blocked by:** 10 (Check a plan, on screen, for the NWWDA plan); 13 (One cited answer through the Foundry agent and the verifier)

**Status:** ready-for-agent
**Area:** app
**Phase:** P1
**Design review:** yes

- [ ] Typing "P130164" lists "Open P130164" first; "IDA-60290" in any of its four forms opens its project; a STEP reference opens the plan check with its row in view; free text offers "Ask this" and nothing happens until the person chooses; "/" focuses the box from anywhere outside a text field.
- [ ] Against a mocked stream, steps are announced through a live region one step at a time (never token by token), then "In short" renders with a [1] marker, the check line's counts from the stream, and the removed box reading "I removed one sentence. It said bids were usually opened within 45 days, and no record supports that number."
- [ ] Hovering or focusing [1] shows an evidence card with the stratum eyebrow, a title, the highlighted excerpt and a source line (DESIGN.md section 5); clicking it opens the drawer at ICR ¶54 with the meta line "Implementation Completion and Results Report · Rajasthan Road Sector Modernization (P130164) · October 10, 2019 · Section III.B · ¶54 · PDF page 23 of 66", as in the Evidence drawer wireframe.
- [ ] The drawer is clamp(400px, 40vw, 600px) wide and leaves the page usable; Escape closes it and focus returns to the marker; reloading with the evidence parameter reopens it; below 768 px it is a full-screen sheet.
- [ ] An opened citation shows a visited state and writes one row per viewer and evidence id to strata.ops.
- [ ] Streaming, error (agent unavailable), refusal and empty states exist and are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations; the check line never uses the success state.
- [ ] On the deployed app, asking the showcase question from the box returns a cited answer through the Foundry agent: the second half of P1's exit criterion.
