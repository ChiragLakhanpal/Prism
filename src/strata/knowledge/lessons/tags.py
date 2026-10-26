"""A lesson's procurement categories and selection methods (ticket 39; the 39 brief, section 4.8).

The two closed lists are the package form's own (config/package_form.toml, its category and method fields), so a
lesson and a package name a category or a method in the same words, STEP's, and the labels people read come from one
place (CLAUDE.md rule 9). A lead sets them in the Lesson editor; each version's are kept in strata.ops.
lesson_version_tags. A lesson that names no method applies to every method, so the library's method filter keeps it.
"""

from __future__ import annotations

from functools import cache

from strata.config import load_package_form

LISTS = {"categories": "category", "methods": "method"}  # a lesson's tag list, by the package form's field


@cache
def options(name: str) -> tuple[tuple[str, str], ...]:
    """The closed list for categories or methods, as (STEP's value, its label), in the form's order."""
    field = load_package_form().field(LISTS[name])
    return tuple((option.value, option.label) for option in field.options)


def label(name: str, value: str) -> str:
    return dict(options(name)).get(value, value)


def valid(name: str, values) -> bool:
    return isinstance(values, list) and all(value in dict(options(name)) for value in values)


def as_dict() -> dict:
    """Both lists as the Lesson editor and the library's filters take them."""
    return {name: [{"key": value, "label": text} for value, text in options(name)] for name in LISTS}
