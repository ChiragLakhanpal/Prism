-- The ISR rating history, read from each ISR's own overall ratings table (src/strata/lakehouse/isr_ratings.py),
-- because the projects API keeps only the latest ratings. One row per rating per ISR the passage reader
-- read. Rebuilt for each project of the run on every run.
--
-- document_id      the ISR's id in the documents API
-- project_id       the project
-- isr_date         the ISR's date (docdt), the day it was archived
-- sequence         its sequence number, as its first page prints it ("Seq No: 7")
-- rating_name      the rating, word for word: Progress towards achievement of PDO, Overall
--                  Implementation Progress (IP) or Overall Risk Rating
-- previous_rating  the rating the ISR before it gave, as this one prints it
-- current_rating   the rating this ISR gives
-- pdf_page         the PDF page that prints it
-- public_from      the ISR's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.isr_ratings (
  document_id STRING NOT NULL,
  project_id STRING NOT NULL,
  isr_date DATE NOT NULL,
  sequence INT,
  rating_name STRING NOT NULL,
  previous_rating STRING,
  current_rating STRING,
  pdf_page INT NOT NULL,
  public_from DATE NOT NULL
)
