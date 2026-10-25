"""The holds that keep a draft from export, one function for each entry in config/drafts.toml's [holds].

Each takes the draft as it stands (Draft below: its state, the view it is seen in, what it holds, the fields people
set and the choices they made) and gives how many items are left and the anchor of the first one, or None when the
hold does not apply. The draft bar names the holds left in the kind's order, as one sentence whose clauses link to
each first anchor (the 36 brief, section 4.5), and the server refuses an export while any is left.

Ticket 35 registered notChecked and preview. Ticket 36 adds owners and ratings (suggested PPSD rows) and
disagreements (every kind), and ticket 39 adds a cited lesson version retired as wrong to the same list.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

STAFF = "staff"


@dataclass(frozen=True)
class Draft:
    """A draft as the holds read it."""

    state: str
    view: str
    kind: str = ""
    content: Mapping = field(default_factory=dict)
    # The latest value of each field a person set, by (row_key, field); the form is ("", "form").
    fields: Mapping = field(default_factory=dict)
    # The report kept for each disagreement, by its id: "lean" or "other".
    choices: Mapping = field(default_factory=dict)
    # Whether the draft page shows disagreement cards, so a warning card can hold export (config/drafts.toml).
    cards_on_drafts: bool = False


@dataclass(frozen=True)
class Held:
    """How many items a hold has left, and the anchor of the first, for the bar's link to it."""

    left: int
    first_anchor: str | None = None


def not_checked(draft: Draft) -> Held | None:
    """Its author has not marked it as checked yet."""
    return Held(1) if draft.state == "draft" else None


def preview(draft: Draft) -> Held | None:
    """It is seen through another view's preview, which can only take things away (spec, "The app")."""
    return Held(1) if draft.view != STAFF else None


def owners(draft: Draft) -> Held | None:
    """A suggested PPSD row with no Risk Owner yet. Only people set owners; Strata never does."""
    from strata.drafts import ppsd_rows

    return ppsd_rows.missing(draft, "owners")


def ratings(draft: Draft) -> Held | None:
    """In the Long Form, a row whose likelihood, impact or overall risk score is not set yet."""
    from strata.drafts import ppsd_rows

    return ppsd_rows.missing(draft, "ratings")


def disagreements(draft: Draft) -> Held | None:
    """A warning disagreement card on the draft with no report kept yet. A warning card ("Two reports disagree")
    changes a claim the draft makes; an info card changes nothing and holds nothing. Until the draft page shows
    cards (ticket 23's card and keep form; cards_on_drafts in config/drafts.toml), no card renders and nothing
    holds, as the 35 brief set."""
    if not draft.cards_on_drafts:
        return None
    open_cards = [found["id"] for found in draft.content.get("disagreements") or ()
                  if found.get("changes_answer") and found["id"] not in draft.choices]
    return Held(len(open_cards), f"disagreement-{open_cards[0]}") if open_cards else None
