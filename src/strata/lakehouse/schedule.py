"""Nightly windows, and whether two of them overlap on any day.

Strata and fairshare share one workspace, one daily compute quota and five concurrent job tasks,
so their nightly jobs run at different hours (docs/PLAN.md section 2). A window is a daily start
time in a time zone and how long the job may run. Two windows overlap on a day when their runs
share any minute, with each run taken as [start, start + length). Time zones matter, because
midnight UTC is 20:00 in Washington in summer and 19:00 in winter.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable
from dataclasses import dataclass
from zoneinfo import ZoneInfo

# Quartz: seconds minutes hours day-of-month month day-of-week [year], with ? for "no value".
DAILY = re.compile(r"^\s*(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\*|\?)\s+\*\s+(\*|\?)(\s+\*)?\s*$")


class ScheduleError(ValueError):
    pass


@dataclass(frozen=True)
class Window:
    name: str
    start: dt.time
    timezone: str
    minutes: int

    def run_on(self, day: dt.date) -> tuple[dt.datetime, dt.datetime]:
        """The run that starts on day, local time, as a UTC start and end."""
        start = dt.datetime.combine(day, self.start, tzinfo=ZoneInfo(self.timezone)).astimezone(dt.UTC)
        return start, start + dt.timedelta(minutes=self.minutes)


def daily_start(quartz: str) -> dt.time:
    """The start time of a Quartz cron expression that runs once a day, such as "0 0 4 * * ?"."""
    match = DAILY.match(quartz)
    if not match:
        raise ScheduleError(f"I can compare only schedules that run once a day at a fixed time, "
                            f"and {quartz!r} is not one.")
    seconds, minutes, hours = (int(part) for part in match.groups()[:3])
    return dt.time(hours, minutes, seconds)


def overlapping_days(window: Window, other: Window, days: Iterable[dt.date]) -> list[dt.date]:
    """The days on which window's run shares a minute with any run of other."""
    found = []
    for day in days:
        start, end = window.run_on(day)
        for offset in (-1, 0, 1):
            other_start, other_end = other.run_on(day + dt.timedelta(days=offset))
            if start < other_end and other_start < end:
                found.append(day)
                break
    return found
