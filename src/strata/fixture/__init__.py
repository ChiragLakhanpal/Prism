"""The fixture: recorded copies of public World Bank sources that every offline test reads.

data/fixture/sources.toml lists every source. `strata.fixture.recorded` reads the recorded
files, and `python -m strata.fixture.record` refetches them and prints a diff.
"""
