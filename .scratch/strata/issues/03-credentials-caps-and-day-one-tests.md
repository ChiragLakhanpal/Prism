# 03: Credentials, Azure caps and the day-one tests (human in the loop)

**What to build:** A person runs one wizard and ends with every credential in place, every Azure cap set, and all ten day-one tests answered with a chosen path. The agent uses the wizard skill to author the wizard; a person runs it, because only they can sign in to the dashboards. Its stages, in order: a Databricks personal access token or service principal (test 7); the Foundry project Strata on wb-strata in resource group WorldBank-demo; the four model deployments (gpt-5.4-mini, gpt-5.4, gpt-5.4-nano on Global Batch, text-embedding-3-large at 1,024 dimensions) each with a tokens-per-minute cap (test 8); Azure budgets with notifications; Application Insights for the app (test 10); an Entra sign-in for Foundry evaluations (test 9); inviting an outside email to the workspace (test 6); and moving the subscription to pay-as-you-go before November 10, 2026. Every key in the repo's example environment file gets a value: secrets go to the main checkout's environment file and the app's secret scope, never into git. The GitHub repo stays out of the wizard (which account owns it is the user's later decision), and grants on the strata catalog come with ticket 04, once the catalog exists. This ticket is workspace work, so it runs alone, with the main checkout's environment file passed to each probe.

Start this ticket together with 01: the person is at the keyboard when the build starts. Write the wizard first and report it to the orchestrator straight away, with the exact command to run it from the main checkout, so the person runs it while you write the probes. The probes are standalone scripts that declare their own dependencies inline, so they need nothing from 01.

The agent also writes one-command probes for the tests a script can answer (test 1 from a notebook, a job and the app; test 2 from a job; test 3 on a PAD of at least 120 pages; test 4 creating an AI Search endpoint and a hybrid index; test 5 the Genie conversation API answering as the token's user; test 10 a trace from the app) and a day-one results document that records, for each test, the result, the evidence and the path chosen: the default, or the gap fill PLAN.md section 14 names. Later tickets read that document to pick their branch.

Read first: docs/PLAN.md sections 2, 14 and 16; ADR 0001; the wizard skill's instructions.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent
**Area:** ops
**Phase:** P0
**Design review:** no

- [ ] The wizard passes a shell syntax check, and a static trace shows every captured value lands where its stage says (the environment file, the secret scope, or nowhere for pure actions), with secrets entered hidden.
- [ ] After the person runs it, the day-one results document lists all ten tests from PLAN.md section 14, each with a result, its evidence (command output or a run link) and a chosen path; none is blank. This is P0's done criterion.
- [ ] A probe reads each of the four deployments and prints a tokens-per-minute limit for every one; the subscription has a budget with notifications.
- [ ] The probes for tests 1, 2, 3, 4, 5 and 10 each run with one command and write their result into the day-one results document.
- [ ] The subscription shows pay-as-you-go, or the results document records a dated step before November 10, 2026 and who will take it.
