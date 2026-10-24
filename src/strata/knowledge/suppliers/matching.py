"""Name matching for supplier rows with no STEP supplier ID: Splink's candidate pairs and their scores.

A STEP supplier ID decides first. candidate_pairs() takes plain rows and gives plain pairs, so the
nightly task calls it the same way on DuckDB and on Databricks (spec, "Data and the lakehouse run").
Splink runs on an in-memory DuckDB inside the task on both engines, because its Spark backend needs
a JAR that serverless compute may not load.

Each row is a Record: a supplier known by its STEP supplier ID, or a row that names a supplier with
no ID (an award from FY2001 to FY2016, or an awarded bidder a notice writes with no ID). A pair
always has a row with no ID on its left: two suppliers with IDs are never compared, so a name never
joins two IDs. Rows are compared only within one country (blocking), and the members of one
joint-venture row never with each other.

Each pair is scored on two comparisons, with the m and u values of config/models.toml's
[supplier_matching]:

- name, after names.normalize(): the same name; the same words in another order; one name the start
  of the other, as a name cut off at the FY2001 to FY2016 dataset's 40 characters is; nearly the same
  (Jaro-Winkler 0.95 or more); alike (0.88 or more); different;
- projects: whether the two rows share a project.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from strata.config import ConfigError, SupplierMatching
from strata.knowledge.suppliers.names import normalize

# Each comparison's levels, most alike first, with the rule that puts a pair in it. Splink adds
# _l and _r to a column's name for the pair's two rows.
LEVELS = {
    "name": (
        ("same_name", "name_norm_l = name_norm_r"),
        ("same_words", "words_l = words_r"),
        ("starts_the_other", "least(length(name_norm_l), length(name_norm_r)) >= 10 AND "
                             "(starts_with(name_norm_l, name_norm_r) OR starts_with(name_norm_r, name_norm_l))"),
        ("nearly_the_same", "jaro_winkler_similarity(name_norm_l, name_norm_r) >= 0.95"),
        ("alike", "jaro_winkler_similarity(name_norm_l, name_norm_r) >= 0.88"),
        ("different", "ELSE"),
    ),
    "projects": (
        ("shared", "list_has_any(projects_l, projects_r)"),
        ("none_shared", "ELSE"),
    ),
}
NO_PROJECTS = "projects_l IS NULL OR projects_r IS NULL OR len(projects_l) = 0 OR len(projects_r) = 0"
# Two rows are compared when they share a country and their first word or the first five letters of
# their name, and at least one of them has no STEP supplier ID.
BLOCKING = (
    "l.country_key = r.country_key AND l.first_word = r.first_word AND l.has_id + r.has_id < 2",
    "l.country_key = r.country_key AND l.compact = r.compact AND l.has_id + r.has_id < 2",
)


@dataclass(frozen=True)
class Record:
    key: str  # the STEP supplier ID, or the row's own key, such as 1536431/1 or OP00054114/2
    name: str
    country: str | None
    projects: tuple[str, ...]
    has_id: bool
    group: str | None  # the source row it shares with its joint-venture partners, never paired with them


@dataclass(frozen=True)
class Pair:
    left: str  # always a row with no STEP supplier ID
    right: str
    probability: float
    weight: float
    name_level: str
    projects_level: str


def _comparison(comparison: str, column: str, model: SupplierMatching, null_rule: str | None) -> dict:
    levels = LEVELS[comparison]
    configured = {level.name: level for level in model.comparisons.get(comparison, ())}
    if set(configured) != {name for name, _ in levels}:
        raise ConfigError(f"In models.toml, supplier_matching.{comparison} must give m and u for exactly these levels: "
                          f"{', '.join(name for name, _ in levels)}.")
    entries = []
    if null_rule:
        entries.append({"sql_condition": null_rule, "label_for_charts": "unknown", "is_null_level": True})
    for name, rule in levels:
        entries.append({"sql_condition": rule, "label_for_charts": name,
                        "m_probability": configured[name].m, "u_probability": configured[name].u})
    return {"output_column_name": column, "comparison_levels": entries}


def settings(model: SupplierMatching) -> dict:
    return {
        "link_type": "dedupe_only",
        "unique_id_column_name": "key",
        "probability_two_random_records_match": model.prior,
        "blocking_rules_to_generate_predictions": list(BLOCKING),
        "comparisons": [_comparison("name", "name_norm", model, None),
                        _comparison("projects", "projects", model, NO_PROJECTS)],
        "retain_intermediate_calculation_columns": True,
        "additional_columns_to_retain": ["group_key"],
    }


def _row(record: Record) -> dict | None:
    name = normalize(record.name)
    country = " ".join((record.country or "").upper().split())
    if not name or not country:
        return None  # nothing to compare, or no country to compare it within
    words = name.split()
    return {"key": record.key, "name_norm": name, "words": " ".join(sorted(words)), "first_word": words[0],
            "compact": name.replace(" ", "")[:5], "country_key": country, "projects": sorted(set(record.projects)),
            "has_id": int(record.has_id), "group_key": record.group or record.key}


def _level(levels: tuple[tuple[str, str], ...], gamma) -> str:
    """Splink numbers a comparison's levels from the most alike down to 0, and the null level -1."""
    if gamma is None or int(gamma) < 0:
        return "unknown"
    return levels[len(levels) - 1 - int(gamma)][0]


def candidate_pairs(records: list[Record], model: SupplierMatching, floor: float) -> list[Pair]:
    """Every pair of rows Splink scores at floor or above, with a row with no STEP supplier ID on the left."""
    from splink import DuckDBAPI, Linker

    rows = [row for row in map(_row, records) if row is not None]
    if not any(row["has_id"] == 0 for row in rows):
        return []
    has_id = {row["key"]: bool(row["has_id"]) for row in rows}
    linker = Linker(DuckDBAPI().register(rows), settings(model), log_level=None)
    found = linker.inference.predict(threshold_match_probability=floor, warning_mode="never").as_record_list()
    pairs = []
    for scored in found:
        if scored["group_key_l"] == scored["group_key_r"]:
            continue
        left, right = scored["key_l"], scored["key_r"]
        if has_id[left] or (not has_id[right] and right < left):
            left, right = right, left
        pairs.append(Pair(left, right, float(scored["match_probability"]), float(scored["match_weight"]),
                          _level(LEVELS["name"], scored["gamma_name_norm"]),
                          _level(LEVELS["projects"], scored["gamma_projects"])))
    logging.getLogger("strata.suppliers").info("Name matching scored %d candidate pairs.", len(pairs))
    return sorted(pairs, key=lambda pair: (pair.left, pair.right))
