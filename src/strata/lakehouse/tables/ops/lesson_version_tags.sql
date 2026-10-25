-- The procurement categories and selection methods a lesson version names (ticket 39; the 39 brief, section 4.8),
-- beside strata.ops.lesson_versions so that table keeps its columns. A lead sets them in the Lesson editor when they
-- add or change a lesson, from the package form's closed lists (config/package_form.toml, the category and method
-- fields). A version with no row here names none: it applies to every category and method, so the library's method
-- filter keeps it. Written with the version it belongs to; a row never changes and never leaves.
--
-- lesson_id    the lesson (strata.ops.lesson_versions)
-- version      the version that names them
-- categories   the procurement categories, as a JSON list of STEP's words, such as ["Works"]
-- methods      the selection methods, as a JSON list of STEP's words, such as ["Request for Bids"]
-- public_from  the day the version was decided (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.lesson_version_tags (
  lesson_id STRING NOT NULL,
  version INT NOT NULL,
  categories STRING NOT NULL,
  methods STRING NOT NULL,
  public_from DATE NOT NULL
)
