# 144: An answer never prints a field name: the agent writes the tool's words for a column, and the verifier removes a sentence that carries one

**What to build:** On October 30, 2026 the demo walkthrough's final capture of the Kenya water package's ask box (KE-NWWDA-541055-CW-RFB, "How long did comparable packages take from notice to signed contract?") showed an answer that prints the raw field name `signed_before_notice` in a sentence meant for a procurement specialist. The tool results carry column names (`src/strata/tools/find_comparables.py` returns rows with keys such as `signed_before_notice`, `no_step_reference`, `no_notice`), and the agent (`src/strata/agent/orchestrator.md`, the tool descriptions in `config/tools.toml`) sometimes copies a key into prose. Make two changes in one place each: (1) every tool result that the agent may quote carries a `words` map from each key the agent might name to the words Strata uses for it (from one registry, `config/tools.toml` or a sibling, next to the tool's description; for the comparables tool: "signed before its notice", "no STEP reference", "no specific procurement notice"), and the agent prompt says to use those words and never a key; (2) the verifier (`src/strata/agent/verifier.py`) treats a sentence that carries a key-shaped token (lowercase words joined by underscores, or a tool or column name from the registry) as failing its check, so it is removed and shown in the removed box like a number no record supports. Tests: a recorded stream with such a sentence loses it; the comparables answer in the recorded fixtures prints the words; the benchmark questions keep their answers. The live proof is the orchestrator's: the same question on the App after the redeploy prints no key, recorded in the catch-up file. Keep the gate under 150 seconds; no design review.

Read first: `src/strata/agent/verifier.py` (the checks and the removed box), `src/strata/agent/orchestrator.md`, `config/tools.toml`, `src/strata/tools/find_comparables.py` (the result's keys), the recorded answer streams under `tests/fixtures/`.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] Each tool result the agent may quote carries its words for every key, from one registry, and the agent prompt says to use them (a test that every key the tools return has words).
- [ ] The verifier removes a sentence that carries a key-shaped token or a registry name, showing it in the removed box (tests on a recorded stream and on the benchmark's answers, which keep passing).
- [ ] On the paid workspace, the Kenya water package question prints no key after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 30, 2026, orchestrator: opened at 03:50 PDT from the walkthrough's final capture; ready to launch on the owner's word.
