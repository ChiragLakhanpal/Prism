-- An assertion: a dated claim a source makes about a project or a package (GLOSSARY.md), such as an
-- ISR's rating of progress, an ICR's account of the mid-term review, or a contract's signing date. It
-- is written by the nightly job's detect_disagreements task (src/strata/knowledge/assertions.py), rebuilt
-- for each project of the run. Both sides of a disagreement are always kept here.
--
-- assertion_id    stable: the evidence id, then the subject and the attribute
-- subject_kind    project or package
-- subject_id      the project ID, or the package's STEP reference
-- attribute       what it is about, as config/evidence_ladder.toml names it, such as pdo_progress
-- attribute_kind  rating, date or amount
-- field_name      the source's own name for it, word for word, such as Progress towards achievement of PDO
-- value           the value as the source gives it: a rating word for word, a judgment's side
--                 (satisfactory or unsatisfactory), a date in ISO form, an amount in US dollars
-- value_form      rating, judgment (a narrative account that gives only a side), date, amount, or status (a plan
--                 row's Process Status before signing, ticket 132)
-- judgment        the side of the line a rating or an account falls on: satisfactory or unsatisfactory;
--                 empty for a date, an amount, or a rating on a scale with no sides, such as risk
-- period_event    the period it describes: report_period (an ISR's own period), whole_project,
--                 mid_term_review, or contract_signing (a package's signing, which each source dates)
-- period_start, period_end   the period's dates: for contract_signing, the signing as this source dates it
-- made_at         the day the source made it: the report's date, the notice's date, the plan's date, or
--                 for an awards dataset's record its signing date
-- public_from     the day its source became public (ADR 0002)
-- replaced_on     the day a later version of its source replaced it: a report re-issued under the same
--                 number (ticket 11's rule), or the next version of the same agency's Procurement Plan
-- evidence_tier   pad, isr, icr, ieg or record (config/evidence_ladder.toml, [tiers])
-- form            rating_field, narrative, contract_record, award_notice or plan_row, for the ladder's
--                 more-specific tie
-- source_key      the source registry's key (config/sources.toml): documents, ieg_ratings, awards,
--                 awards_fy2001_2016 or notices
-- document_id     the documents API id of its report or plan version, the notice's id, the contract's
--                 number, or the IEG evaluation's key
-- document_type   the report's type in the documents API, or the record's kind
-- report_number, version   the report's number and its version of that number (ticket 11)
-- sequence        its place in its series, such as 7 for ISR 7
-- passage_id      the passage it rests on, or the record's key in its table
-- evidence_id     the id a tool returns for that passage or record, so a claim's citation finds it
-- pdf_page        the PDF page of the passage
-- quote           the words on the page it rests on, for an assertion read from text
-- read_by         what read it: the batch model's deployment, or the reader of a record
CREATE TABLE IF NOT EXISTS strata.gold.assertion (
  assertion_id STRING NOT NULL,
  subject_kind STRING NOT NULL,
  subject_id STRING NOT NULL,
  project_id STRING NOT NULL,
  attribute STRING NOT NULL,
  attribute_kind STRING NOT NULL,
  field_name STRING NOT NULL,
  value STRING NOT NULL,
  value_form STRING NOT NULL,
  judgment STRING,
  period_event STRING NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  made_at DATE NOT NULL,
  replaced_on DATE,
  evidence_tier STRING NOT NULL,
  form STRING NOT NULL,
  source_key STRING NOT NULL,
  document_id STRING NOT NULL,
  document_type STRING,
  report_number STRING,
  version INT,
  sequence INT,
  passage_id STRING NOT NULL,
  evidence_id STRING NOT NULL,
  pdf_page INT,
  quote STRING,
  read_by STRING NOT NULL,
  public_from DATE NOT NULL
)
