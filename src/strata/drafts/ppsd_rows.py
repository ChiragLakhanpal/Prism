"""The suggest-PPSD-rows workflow: suggested risk rows for the borrower's PPSD (ticket 36).

table_i() compares a package's cost estimate with the PPSD guidance's Table I (config/thresholds.toml's
[ppsd_table_i]) to say whether the Long Form may be offered.
"""

from __future__ import annotations

from decimal import Decimal

from strata.config import Thresholds


def _money(value: Decimal | None) -> str | None:
    return None if value is None else f"{Decimal(value):.2f}"


def table_i(limits: Thresholds, category: str | None, amount: Decimal | None) -> dict:
    """Whether the package's whole cost estimate is at or above Table I's threshold for its category, at the
    risk level the thresholds file offers the Long Form from. The amount and the threshold come back as text with
    two decimals, as tools write amounts; with no cost estimate or no category, nothing is compared."""
    level = limits.value("ppsd_table_i.offer_long_form_at")
    rows = limits.value("ppsd_table_i.row")
    if amount is None or category not in rows:
        return {"applies": False, "amount": _money(amount), "threshold": None, "currency": "USD", "category": category,
                "risk_level": level}
    threshold = Decimal(limits.value(f"ppsd_table_i.from_usd.{rows[category]}")[level])
    return {"applies": Decimal(amount) >= threshold, "amount": _money(amount), "threshold": _money(threshold),
            "currency": "USD", "category": category, "risk_level": level}
