"""What the nightly job's tests share (ticket 43): a clock that moves on each time it is read, and an engine a
draft store cannot close."""

import datetime as dt


def clock(start: dt.datetime, step: dt.timedelta = dt.timedelta(milliseconds=1)):
    """A clock that moves on by step each time a task reads it, so each try's start and finish keep their order."""
    ticks = iter(range(10**7))
    return lambda: start + step * next(ticks)


class Unclosed:
    """The test's engine, which the draft store's close leaves open."""

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def close(self):
        pass
