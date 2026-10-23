"""The knowledge model: passages made searchable (ticket 11), and later lessons, links and assertions.

- sectors.py  the word a passage's header uses for a project's sector
- embed.py    the embedding adapters: text-embedding-3-large on Azure OpenAI, and the offline stand-in
- shields.py  the Prompt Shields adapters: Azure AI Content Safety, and the offline stand-in
- search.py   hybrid search over the passages: AI Search on the workspace, the fixture search offline,
              and the AI Search index the passages sync to
"""
