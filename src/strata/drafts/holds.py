"""The holds that keep a draft from export, one function for each entry in config/drafts.toml's [holds].

Each takes the draft's state now and the view it is seen in, and says whether the hold applies. Ticket 36
adds owners, ratings and disagreements, and ticket 39 a cited lesson version retired as wrong.
"""

STAFF = "staff"


def not_checked(state: str, view: str) -> bool:
    """Its author has not marked it as checked yet."""
    return state == "draft"


def preview(state: str, view: str) -> bool:
    """It is seen through another view's preview, which can only take things away (spec, "The app")."""
    return view != STAFF
