# The agent decides; the app runs its tools as the viewer

The Strata agent lives in Microsoft Foundry (ADR 0001) as prompt agents whose instructions are versioned in this repo. When it needs data it returns a function call, and the Databricks App runs that tool with the viewer's own token against Genie, AI Search and SQL, then hands the result back. The app therefore holds every row and passage an answer relies on, so the verifier can check each sentence against them, and each viewer sees only what their own permissions allow. Multi-step jobs (planning a package, drafting a PPSD section, reviewing new lessons) are Microsoft Agent Framework workflows in code.

## Considered options

- **A Foundry-hosted agent calling Databricks directly:** one shared token, so every viewer sees the same data, and the rows an answer used never reach the verifier.
- **Foundry portal workflows:** they retire on December 1, 2026.

## Consequences

- The app sits on every tool call's path, so the agent cannot answer on its own outside the app.
- A later Teams or Copilot channel needs its own tool host, or, in production, the Azure Databricks connector with each user's own sign-in.
