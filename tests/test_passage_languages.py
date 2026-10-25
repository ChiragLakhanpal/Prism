"""Every passage's language, set and checked across the slice, at seam 1 (ticket 42).

Each passage takes its language from its document's record in the Documents API (its lang field, mapped by
config/languages.toml), and the passage reader checks a sample of the passages against a language detector that
reads only their words, so the check does not rest on how the language was set. The fixture holds the French
completion report for P127203 (ICR4990, data/fixture/README.md) beside English reports and notices.
"""

import datetime as dt

from strata.config import load_languages, load_thresholds
from strata.knowledge import language
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine

THRESHOLDS = load_thresholds()
FRENCH_ICR = "33407968"  # config/slice.toml's stress shelf: the completion report in French


def readiness(engine, measure):
    [row] = engine.connection.execute(
        "SELECT count, denominator, detail FROM strata.ops.data_readiness WHERE measure = ? AND subject = 'all'",
        [measure]).fetchall()
    return row


def test_every_passage_in_the_slice_has_a_language_the_registry_knows(fixture_db):
    known = {entry.code for entry in load_languages().languages}
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        by_language = dict(engine.connection.execute(
            "SELECT language, count(*) FROM strata.silver.passages GROUP BY language").fetchall())
        french_icr = engine.connection.execute(
            "SELECT DISTINCT language FROM strata.silver.passages WHERE document_id = ?", [FRENCH_ICR]).fetchall()
        count, denominator, _ = readiness(engine, "passages_language_set")

    assert set(by_language) <= known and "und" not in by_language
    assert french_icr == [("fr",)]
    assert (count, denominator) == (sum(by_language.values()), sum(by_language.values()))


def test_a_sample_of_50_passages_agrees_with_a_language_detector_that_reads_only_their_words(fixture_db):
    size = THRESHOLDS.value("lang.sample_size")
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        sampled = engine.connection.execute(
            "SELECT passage_id, language, detected, confidence, agrees, detector FROM strata.ops.passage_language_checks"
        ).fetchall()
        count, denominator, detail = readiness(engine, "passage_language_sample_agrees")

    assert size == 50 and len(sampled) == size and denominator == size
    languages = {row[1] for row in sampled}
    assert languages == {"en", "fr"}
    # The sample is shared equally between the languages the passages are written in.
    assert sum(1 for row in sampled if row[1] == "fr") == size // len(languages)
    assert count == sum(1 for row in sampled if row[4]) == size
    assert all(row[2] == row[1] and row[3] > 0 for row in sampled)
    assert {row[5] for row in sampled} == {language.LangidDetector.name}
    assert "50" in detail


def test_a_passage_whose_language_was_set_wrong_disagrees_with_the_detector(tmp_path):
    """A French paragraph that its record called English is counted as a disagreement, and the check names it."""
    french = ("Le Projet a permis de reconstruire les infrastructures électriques et d'améliorer l'accès à "
              "l'électricité dans les zones urbaines et rurales, malgré des retards importants dans la passation "
              "des marchés de travaux.")
    english = ("The project rebuilt the electricity infrastructure and improved access to electricity in urban and "
               "rural areas, despite long delays in the procurement of the works contracts, which the implementing "
               "agency had to advertise again.")
    with DuckDBEngine.open(tmp_path / "check.duckdb") as engine:
        catalog.build(engine)
        rows = [(f"d1/v1/{n}", "en", text) for n, text in enumerate([french, english, english], 1)]
        rows += [(f"d2/v1/{n}", "fr", french) for n in range(1, 4)]
        for passage_id, code, text in rows:
            engine.connection.execute(
                "INSERT INTO strata.silver.passages VALUES (?, ?, 'P000001', 'Implementation Completion and Results "
                "Report', 1, 'I', '1', true, 1, 1, 1, 1, '1', ?, 'A', 'paragraph', false, NULL, NULL, NULL, NULL, "
                "'ICR', ?, 40, 'hash', DATE '2021-07-29')", [passage_id, passage_id.split("/")[0], code, text])
        checked = language.check(engine, "run-1", dt.datetime(2026, 10, 23, 9, tzinfo=dt.UTC), THRESHOLDS,
                                 language.LangidDetector())
        disagreeing = engine.connection.execute(
            "SELECT passage_id, language, detected FROM strata.ops.passage_language_checks WHERE NOT agrees").fetchall()
        count, denominator, _ = readiness(engine, "passage_language_sample_agrees")

    assert checked == (5, 6)
    assert disagreeing == [("d1/v1/1", "en", "fr")]
    assert (count, denominator) == (5, 6)
