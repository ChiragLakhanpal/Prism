"""Prism's deep research (tickets 147 to 150): what is happening on the ground at a project, from public sources outside the
World Bank's records and from the Bank's own narrative.

- config/research.toml is the registry of its sources (strata.config.load_research).
- project.py builds ProjectFacts, what a reader knows of the project, from the project's record.
- fetching.py is how a reader reaches a source: the live fetch with Prism's named agent, the offline fetch over the
  recordings, the pacing and the cache.
- sources/ holds one reader per source behind one interface, read(source, project, fetch, engine, now).
- items.py makes the one item shape every later ticket reads, and store.py keeps runs, their items and the briefs
  written from them in strata.ops.
- run.py is the run the route streams (ticket 148): the sources read, the brief written by writer.py from brief.py's
  message, and every sentence checked by the verifier.
"""
