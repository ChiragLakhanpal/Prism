# Databricks for data and knowledge, Microsoft Foundry for the agent, Azure for what Free Edition lacks

Prism's data, knowledge model, search, structured questions, predictive models and app run on Databricks Free Edition, because the panel asked for a Databricks-native lakehouse and Unity Catalog keeps lineage, permissions and incremental sync in one place. The conversational agent, its guardrails, evaluations and traces live in Microsoft Foundry: Databricks marked Knowledge Assistant and Supervisor Agent legacy on October 12, 2026, its code-first Agent Bricks runtime is in Beta and unconfirmed on Free Edition, while Foundry's agent service, guardrails and evaluations are generally available. Anything Free Edition lacks or caps is filled by an Azure service in the same subscription.

## Considered options

- **All Databricks** (Agent Bricks CLI on Agent Runtime): what the panel named, but in Beta, unconfirmed on Free Edition, OAuth-only for Apps, and it would take one of Free Edition's three app slots.
- **All Azure** (Azure AI Search, Fabric or Azure SQL for the data): drops the lakehouse the panel asked for and splits governance across two platforms.

## Consequences

- Databricks still supplies the Agent Bricks pieces: a Genie Agent for structured questions, AI Functions for parsing and extraction, and AI Search for retrieval.
- Every call between Foundry and Databricks crosses an identity boundary. Whether tools run as the viewer or as one service identity is a separate decision.
- Azure spend is bounded by a US$200 credit, so every Azure service needs a hard cap, not only a budget alert.
