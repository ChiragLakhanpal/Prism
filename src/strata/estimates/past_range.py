"""The past range: Kaplan-Meier over comparable packages, with packages still open kept as censored.

Each comparable is one observation: the days from its specific procurement notice to its signed
contract, or, for a package still open, the days so far, counted as not signed yet. Plotting only
the signed packages would make every range look shorter than it was (docs/PLAN.md section 7).

The curve is computed with exact fractions, so a share that lands exactly on a quantile, such as
half of 40, is never read as 0.4999. The quantile for a share p is the first day on which the share
of packages not yet signed is 1 - p or less, the rule lifelines' qth_survival_time and statsmodels'
SurvfuncRight.quantile follow. It is None when the curve never gets there, because too many
packages are still open.

Months are days divided by 30.4375 (365.25 / 12), rounded to one decimal, half up. That is the one
rounding every month Strata states takes, so a dot, a quantile and the plan line agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

DAYS_PER_MONTH = Decimal("30.4375")  # 365.25 / 12
TENTH = Decimal("0.1")


def months(days: int) -> Decimal:
    """Days as months, to one decimal."""
    return (Decimal(days) / DAYS_PER_MONTH).quantize(TENTH, ROUND_HALF_UP)


@dataclass(frozen=True)
class Observation:
    days: int
    signed: bool  # False: still open, kept as not signed yet


def survival(observations: list[Observation]) -> list[tuple[int, Fraction]]:
    """The Kaplan-Meier curve: on each day a package was signed, the share not yet signed after it."""
    curve, share = [], Fraction(1)
    at_risk = len(observations)
    for day in sorted({o.days for o in observations}):
        on_day = [o for o in observations if o.days == day]
        signed = sum(1 for o in on_day if o.signed)
        if signed:
            share *= Fraction(at_risk - signed, at_risk)
            curve.append((day, share))
        at_risk -= len(on_day)  # a package still open on this day leaves the risk set after it
    return curve


def quantile(curve: list[tuple[int, Fraction]], share: Fraction) -> int | None:
    """The first day by which this share of the packages was signed, or None if the curve never gets there."""
    for day, left in curve:
        if left <= 1 - share:
            return day
    return None


QUARTERS = {"q25": Fraction(1, 4), "q50": Fraction(1, 2), "q75": Fraction(3, 4), "q80": Fraction(4, 5)}


def quartiles(observations: list[Observation]) -> dict[str, int | None]:
    """The middle half (q25 to q75), the middle (q50) and the day 8 in 10 were signed by (q80), in days."""
    curve = survival(observations)
    return {name: quantile(curve, share) for name, share in QUARTERS.items()}


def quantile_dots(observations: list[Observation], count: int) -> list[tuple[int, int | None]]:
    """count dots, each standing for an equal share of the packages: dot k sits at the share
    (k - 1/2) / count. A dot the curve never reaches has no day."""
    curve = survival(observations)
    return [(k, quantile(curve, Fraction(2 * k - 1, 2 * count))) for k in range(1, count + 1)]
