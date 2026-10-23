"""The word a passage's header uses for its project's sector, from the projects API's sector codes.

A passage's header names the sector in a word ("ICR, P130164, India, roads, III.B, ¶54, p.23"). The
passage's sector, which search_passages filters on, is its project's one sector in Strata's
taxonomy (strata.gold.project.sector, from config/sectors.toml), so this table only picks the word.

Each code is the projects API's sector code (sectorcode) with its name in the 2016 taxonomy (the
FY17 names in mjsector) and the key in config/sectors.toml of the sector it belongs to. The word
comes from the project's first code in its one sector that is not a public-administration code,
since those name who governs a sector rather than the work, or else from its first such code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sector:
    name: str  # the projects API's name for the code
    sector: str  # its sector's key in config/sectors.toml
    word: str  # the word a passage's header uses
    administration: bool = False


SECTORS: dict[str, Sector] = {
    "TA": Sector("Aviation", "transport", "aviation"),
    "TF": Sector("Public Administration - Transportation", "transport", "transport", administration=True),
    "TI": Sector("Rural and Inter-Urban Roads", "transport", "roads"),
    "TP": Sector("Ports/Waterways", "transport", "ports"),
    "TV": Sector("Urban Transport", "transport", "urban transport"),
    "TW": Sector("Railways", "transport", "railways"),
    "TZ": Sector("Other Transportation", "transport", "transport"),
    "WA": Sector("Public Administration - Water, Sanitation and Waste Management", "water", "water",
                 administration=True),
    "WC": Sector("Sanitation", "water", "water"),
    "WD": Sector("Waste Management", "water", "waste"),
    "WF": Sector("Water Supply", "water", "water"),
    "WZ": Sector("Other Water Supply, Sanitation and Waste Management", "water", "water"),
}


def main_sector(codes: str | None, sector: str | None = None) -> Sector | None:
    """The code whose word a passage's header uses, from a project's sector codes as the projects API
    lists them: the first code in the project's one sector that is not a public-administration code,
    else the first such code in any sector."""
    known = [SECTORS[code.strip()] for code in (codes or "").split(",") if code.strip() in SECTORS]
    work = [found for found in known if not found.administration]
    return next((found for found in work if found.sector == sector), next(iter(work), known[0] if known else None))
