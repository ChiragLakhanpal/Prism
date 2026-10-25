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

import datetime as dt
import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

DAYS_PER_MONTH = Decimal("30.4375")  # 365.25 / 12
TENTH = Decimal("0.1")


def months(days: int) -> Decimal:
    """Days as months, to one decimal."""
    return (Decimal(days) / DAYS_PER_MONTH).quantize(TENTH, ROUND_HALF_UP)


def rounded(value: int | float | Decimal | Fraction, places: int = 0) -> Decimal:
    """A number to a number of decimal places, half up: the one rounding the estimates use. A float is
    read as it prints, so 0.745 is 0.745 and not the binary number just below it."""
    if isinstance(value, Fraction):
        exact = Decimal(value.numerator) / Decimal(value.denominator)
    else:
        exact = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    return exact.quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)


def whole(value: int | float | Decimal | Fraction) -> int:
    """A number rounded to a whole number, half up."""
    return int(rounded(value))


def as_date(value) -> dt.date | None:
    """A date from a stored value: a date, a timestamp's day, or ISO text; None when there is none."""
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


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


def dot_packages(observations: list[Observation], count: int) -> list[list[int]]:
    """The packages each of count quantile dots stands for, as indexes into observations, in their order.

    Dot k stands for the k-th of count equal shares of the curve. Each signed package holds the share
    its signing took off the curve: on a day s of the n packages at risk were signed, each of them holds
    1/n of the share not yet signed before it. The packages still open after the last signing hold what
    is left, equally. A package still open that left the risk set earlier holds nothing, since
    Kaplan-Meier passed its share to the packages after it, so no dot stands for it. A package belongs to
    the dot whose share holds the middle of its own. Packages on the same day are taken in the order
    given, so the caller orders ties. A dot whose share holds no package's middle, because one package's
    share spans all of it, stands for the package whose share holds the dot itself, which is the
    package on whose day the dot sits."""
    index_by_day: dict[int, list[int]] = {}
    for index, observation in enumerate(observations):
        index_by_day.setdefault(observation.days, []).append(index)
    held: list[tuple[int, Fraction, Fraction]] = []  # (index, start, end) of each share, in curve order
    start, left, at_risk = Fraction(0), Fraction(1), len(observations)
    after: list[int] = []  # the packages still at risk after the last signing so far
    for day in sorted(index_by_day):
        on_day = index_by_day[day]
        signed = [index for index in on_day if observations[index].signed]
        if signed:
            each = left / at_risk
            for index in signed:
                held.append((index, start, start + each))
                start += each
            left -= each * len(signed)
            after = []
        after += [index for index in on_day if not observations[index].signed]
        at_risk -= len(on_day)
    for index in after:
        each = left / len(after)
        held.append((index, start, start + each))
        start += each

    dots: list[list[int]] = [[] for _ in range(count)]
    for index, begin, end in held:
        middle = (begin + end) / 2
        dots[min(max(math.ceil(middle * count), 1), count) - 1].append(index)
    for k, members in enumerate(dots, start=1):
        if not members:
            at = Fraction(2 * k - 1, 2 * count)
            members.extend(index for index, begin, end in held if begin < at <= end)
    return dots
