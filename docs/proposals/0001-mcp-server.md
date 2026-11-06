# Proposal 1: Prism as an MCP server

**From:** ProcIntel, `src/procintel/mcp_server.py` (Surya Yadav, October to November 2026)
**Status:** proposed, November 6, 2026

## The idea, as ProcIntel built it

ProcIntel's engine is also an MCP server, so an assistant (Claude, Copilot, any MCP client) can use it as a tool instead of reading raw documents. It is a thin client of the backend API: sign-in, the guardrails and the feedback log apply exactly as they do for the website, and every tool is read-only. Four tools: `list_options` (the codes `assess_package` accepts), `assess_package` (typical and slow-case days from tender notice to award, risk flags with their evidence, lessons, similar contracts, caveats), `ask_evidence` (a question answered only from the reports, every sentence with numbered citations checked against the passage it cites, refused when the reports do not cover it) and `get_passage` (a cited passage in full, by its id). It runs over stdio for a desktop client or as Streamable HTTP on a local port.

## How it would work in Prism

Prism already has the pieces the server needs: 14 tools in one registry (`config/tools.toml`), one `call` that runs any of them as the viewer, a verifier that checks every answer, and evidence ids that open a record or a passage. The MCP server is one more client of that registry, not a second engine.

- **Tools.** Every registry tool becomes an MCP tool with the registry's description and parameters, generated from `config/tools.toml` the way the agent's tool list is, so a new tool in the registry is a new MCP tool with no other change. Two more, as ProcIntel has them: `ask` (the answer stream run to its end, returned as the kept sentences with their evidence ids, the removed sentences with their reasons, and the check line) and `get_evidence` (a record or passage by its evidence id, as the evidence drawer shows it).
- **Checks.** The verifier runs on every `ask`; a tool result keeps its coverage line and its abstention. Nothing reaches the client that would not reach the screen.
- **Who is asking.** The server runs as a signed-in viewer, with that viewer's view (World Bank staff, implementing agency officer or the public) and the same access rule for private uploads, so an assistant sees exactly what its person would see in the app. No account, no answer.
- **Where it runs.** Over stdio from a checkout (`python -m strata.mcp`) and as Streamable HTTP beside the App's routes, behind the App's sign-in.

## What changes from ProcIntel

ProcIntel's `assess_package` folds a timeline, risks, lessons and comparables into one call; Prism keeps them as the separate tools they are (`find_comparables`, `estimate_time`, `rebidding_risk`, `get_lessons`, `project_signals`), because each has its own verifier contract and benchmark question. The wording follows Prism's rules: a signal is a reason to look, never a flag.

## Open questions

1. Which views may use the server: staff only at first, or every view the App has?
2. Should `ask` stream, or return only when the verifier is done?
3. A benchmark question per MCP tool, or one for the server as a whole?
