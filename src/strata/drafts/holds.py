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
    # The report its author kept on each disagreement, by the disagreement's id: "lean" or "other".
    choices: Mapping = field(default_factory=dict)
    # Whether the draft page shows disagreement cards, so a warning card can hold export (config/drafts.toml).
    cards_on_drafts: bool = False
    # Ticket 39: the open version notices on its rows (strata.knowledge.lessons.notices.row_notices).
    notices: tuple = ()


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
    """A suggested PPSD row with no Risk Owner yet. Only people set owners; Prism never does."""
    from strata.drafts import ppsd_rows

    return ppsd_rows.missing(draft, "owners")


def ratings(draft: Draft) -> Held | None:
    """In the Long Form, a row whose likelihood, impact or overall risk score is not set yet."""
    from strata.drafts import ppsd_rows

    return ppsd_rows.missing(draft, "ratings")


def disagreement_key(found: Mapping) -> str:
    """The id a disagreement check 6 attached is kept by (strata.gold.disagreement's disagreement_id), which the card's
    choices are recorded under (ticket 23's strata.ops.disagreement_choices) and the card's anchor names."""
    return found.get("disagreement_id") or str(found["id"]).rsplit(":", 1)[-1]


def disagreements(draft: Draft) -> Held | None:
    """A warning disagreement card on the draft whose author has kept neither report yet. A warning card ("Two
    reports disagree") changes a claim the draft makes; an info card changes nothing and holds nothing. Keeping
    either report on the card (ticket 23's keep action, with the draft's id) resolves it. With cards_on_drafts off
    in config/drafts.toml, no card renders and nothing holds, as the 35 brief set."""
    if not draft.cards_on_drafts:
        return None
    open_cards = [disagreement_key(found) for found in draft.content.get("disagreements") or ()
                  if found.get("changes_answer") and disagreement_key(found) not in draft.choices]
    return Held(len(open_cards), f"disagreement-{open_cards[0]}") if open_cards else None


def lesson_retired_wrong(draft: Draft) -> Held | None:
    """A row that cites a lesson a lead retired as wrong, until its author removes the row or keeps it with a reason
    (ticket 39; spec story 87: export is blocked only by a version retired as wrong). A changed lesson, or one retired
    as out of date, holds nothing."""
    held = [notice for notice in draft.notices if notice.get("holds_export")]
    return Held(len(held), held[0]["anchor"]) if held else None
