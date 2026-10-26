"""The technical proposal (ticket 46): docs/proposal.md, built from docs/proposal/source.md.

Every number in the proposal links to a result the build measured (Annex 1) or to the setting that fixes it
(Annex 2), and nothing is typed: the build fills each one from a dated snapshot of the measures and from the
registries and config files (CLAUDE.md rules 1, 4 and 9). The parts:

- numbers.py   the number check, which reads Markdown or HTML, so the deck (ticket 47) runs it too
- register.py  the results register and the settings register: what each value is and where it comes from
- snapshot.py  the pull: each result's query, run through the engine adapter, into one dated JSON file
- figures.py   the nine figures, drawn as SVG from the registries and the snapshot
- build.py     the build: placeholders filled, paragraphs numbered, references resolved, annexes written
- __main__.py  the command: pull, build, check and readme
"""
