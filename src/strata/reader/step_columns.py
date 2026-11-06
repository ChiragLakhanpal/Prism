"""The STEP column registry (ticket 38): STEP's plan columns, word for word and in STEP's order, as an upload is read
and as the STEP rows CSV is written.

STEP's names live in src/strata/reader/step.py (COLUMNS for the descriptive columns, STEPS for the steps, with
STEP_ALIASES for an older name), and config/uploads.toml says what Prism does with each: whether the reading needs
it, and whether the CSV fills it with a planned date, copies the officer's value or leaves it empty for people and
STEP. This module joins the two, so no name is written a third time (CLAUDE.md rule 4), and checks that the
registry lists every one of STEP's columns, in order.

The web app reads the lists it shows ("Show the columns I read", the columns the CSV leaves empty) from the server,
never from its own copy, so the names stay defined once.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from strata.config import ConfigError, Uploads, load_uploads
from strata.reader.step import COLUMNS, STEP_ALIASES, STEPS, squash

NAMES = {key: name for name, key in COLUMNS.items()}  # each descriptive column's key -> STEP's name
PLANNED, ACTUAL = "Planned", "Actual"  # STEP's words under each step, in its second header row
REFERENCE, DESCRIPTION = "activity_reference_no", "description"  # the two halves of STEP's first column


@dataclass(frozen=True)
class CsvColumn:
    """One column of the STEP rows CSV: its name, what fills it, and the value it holds."""

    name: str
    fill: str  # planned, copied or left
    field: str  # a descriptive column's key, activity_reference_no or description, or step for a step column
    step: str | None = None  # STEP's name for the step
    head: str | None = None  # Planned or Actual


@dataclass(frozen=True)
class Registry:
    uploads: Uploads

    @property
    def halves(self) -> tuple[str, str]:
        """Activity Reference No. / Description, as its two halves."""
        reference, description = NAMES["activity"].split(" / ")
        return reference, description

    def needed(self) -> list[str]:
        """The columns a reading needs, by STEP's names."""
        return [NAMES[column.key] for column in self.uploads.columns if column.need]

    def optional(self) -> list[str]:
        """The descriptive columns read when a file has them, by STEP's names, then each step's name, whose Planned
        and Actual dates are read."""
        return [NAMES[column.key] for column in self.uploads.columns if not column.need] + list(STEPS)

    def step_header(self, step: str, head: str) -> str:
        return self.uploads.one_row.format(step=step, head=head)

    def csv_columns(self) -> list[CsvColumn]:
        """The STEP rows CSV's columns, in STEP's order: the descriptive columns, then each step's Planned and Actual."""
        columns = []
        for column in self.uploads.columns:
            if column.csv == "split":
                reference, description = self.halves
                columns += [CsvColumn(reference, "left", REFERENCE), CsvColumn(description, "copied", DESCRIPTION)]
            else:
                columns.append(CsvColumn(NAMES[column.key], column.csv, column.key))
        for step in STEPS:
            columns.append(CsvColumn(self.step_header(step, PLANNED), self.uploads.step_planned, "step", step, PLANNED))
            columns.append(CsvColumn(self.step_header(step, ACTUAL), self.uploads.step_actual, "step", step, ACTUAL))
        return columns

    def left_to_people(self) -> list[str]:
        """The CSV's columns Prism leaves empty, by name, in order."""
        return [column.name for column in self.csv_columns() if column.fill == "left"]

    def header_names(self) -> dict[str, str]:
        """Each header a reading matches, squashed (no spaces, lower case), to the column it names: a descriptive
        column's key, or one of the activity column's halves. Aliases come from the registry's [aliases]."""
        names = {squash(NAMES[column.key]): column.key for column in self.uploads.columns}
        reference, description = self.halves
        names |= {squash(reference): REFERENCE, squash(description): DESCRIPTION}
        for key, aliases in self.uploads.aliases.items():
            names |= {squash(alias): key for alias in aliases}
        return names

    @staticmethod
    def step_names() -> dict[str, str]:
        """Each step name a reading matches, squashed, to STEP's name for it."""
        return {squash(name): name for name in STEPS} | {squash(old): new for old, new in STEP_ALIASES.items()}


@cache
def registry() -> Registry:
    """The registry, checked: config/uploads.toml lists every one of STEP's descriptive columns, in STEP's order, and
    names a column only by its key in step.py's COLUMNS."""
    uploads = load_uploads()
    listed = [column.key for column in uploads.columns]
    if listed != list(COLUMNS.values()):
        raise ConfigError("In uploads.toml, [columns] must list each key of src/strata/reader/step.py's COLUMNS once, "
                          f"in its order: {', '.join(COLUMNS.values())}.")
    unknown = sorted(set(uploads.aliases) - set(COLUMNS.values()) - {REFERENCE, DESCRIPTION})
    if unknown:
        raise ConfigError(f"In uploads.toml, [aliases] names {', '.join(unknown)}, which is not a column key.")
    return Registry(uploads)
