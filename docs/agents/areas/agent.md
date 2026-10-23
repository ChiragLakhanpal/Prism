# Area brief: agent

Tickets with `Area: agent` build the Foundry agents, the tools, the workflows, the verifier and the guardrails.

Read: `docs/PLAN.md` section 6, `docs/adr/0001` and `0003`, and the blueprint's "Checking an answer" section (`docs/blueprint/strata-blueprint.html`).

- The agent decides; the app runs each tool as the viewer and keeps every row and passage the answer uses (ADR 0003).
- Numbers come from tools, at the same rounding. A derived figure is a tool column, never model arithmetic.
- Answers come back as claims with evidence ids. The verifier's six checks run on every answer, and a sentence that fails is removed and shown.
- Agent rules live in the Foundry instructions, versioned in the repo. Messages carry data only, because Prompt Shields refuses data that contains rule-like sentences.
- Multi-step jobs are Microsoft Agent Framework workflows in code, and every draft ends with a person marking it checked.
- Each refusal in PLAN.md section 6 is a must-refuse benchmark question.
- Offline tests use recorded model outputs, so the gate needs no network.
