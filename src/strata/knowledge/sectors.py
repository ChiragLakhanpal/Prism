"""The words a passage uses for its project's sector, from the projects API's sector codes.

A passage's header names the sector in a word ("ICR, P130164, India, roads, III.B, ¶54, p.23"), and
search_passages filters on the slice's sectors (config/slice.toml: water and transport). This is the
one place both come from. When ticket 17 maps the two sector taxonomies to one, it replaces this
table, and the passages take their sector from that mapping.

Each code is the projects API's sector code (sectorcode) with its name in the 2016 taxonomy (the
FY17 names in mjsector). A project's header word comes from its first code that is not a
public-administration code, since those name who governs a sector rather than the work.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sector:
    name: str  # the projects API's name for the code
    slice_sector: str  # the slice file's sector it belongs to
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


def main_sector(codes: str | None) -> Sector | None:
    """A project's sector for its passages, from its sector codes as the projects API lists them."""
    known = [SECTORS[code.strip()] for code in (codes or "").split(",") if code.strip() in SECTORS]
    return next((sector for sector in known if not sector.administration), known[0] if known else None)
