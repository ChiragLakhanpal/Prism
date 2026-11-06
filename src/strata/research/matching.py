"""Whether a feed entry or a post is about the project (ticket 147).

An agency's short name in capitals (CWWDA, NWWDA) matches only in capitals, as a word; any other name (Mowasco,
Tavevo, the project's own name, a place) matches as words whatever their capitals. A place counts only together with
one of the sector's words (config/research.toml, [sector_words]), so a story about Mombasa's football never comes in;
for a post, an agency's name needs a sector word too, so a tag alone never brings a post in.
"""

from __future__ import annotations

import re

from strata.config import load_research_client
from strata.research.project import ProjectFacts


def _named(name: str, text: str) -> bool:
    flags = 0 if name.isupper() else re.I
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text, flags) is not None


def sector_words(project: ProjectFacts) -> tuple[str, ...]:
    return load_research_client().sector_words.get(project.sector_key or "", ())


def names_agency(project: ProjectFacts, text: str) -> bool:
    return any(_named(name, text) for name in project.short_names) or (
        bool(project.project_name) and _named(project.project_name, text))


def names_place(project: ProjectFacts, text: str) -> bool:
    return any(_named(place, text) for place in project.place_names)


def names_sector(project: ProjectFacts, text: str) -> bool:
    return any(_named(word, text) for word in sector_words(project))


def about_the_project(project: ProjectFacts, text: str, *, agency_alone: bool) -> bool:
    """Whether the text is about the project: an agency or the project's name (alone, when agency_alone), or a place,
    together with a sector word."""
    if agency_alone and names_agency(project, text):
        return True
    return (names_agency(project, text) or names_place(project, text)) and names_sector(project, text)


def tag(name: str) -> str:
    """A name as a hashtag is written: West Pokot is westpokot."""
    return re.sub(r"[^0-9a-z]", "", name.lower())
