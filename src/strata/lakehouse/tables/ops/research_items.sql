-- One row for each item a deep research run read (ticket 147), in the one shape every later ticket reads
-- (src/strata/research/items.py): keyed by evidence_id within its run. An item read again in a later run keeps the
-- read_on of the first run that read it. Written as the app's own service principal before the run's row in
-- strata.ops.research_runs. Every item is public: a source's own words, contact details stripped, with its address.
--
-- evidence_id   strata.research.item:<project_id>/<source key>/<item key>
-- run_id        the run that read it (strata.ops.research_runs)
-- project_id    the project researched
-- source_key    the registry's key for its source (config/research.toml)
-- kind          the registry's kind: bank_report, procurement, news, complaint, social, satellite or field_photo
-- source        the source as JSON: key, label, kind, license and url_of_source
-- title         one line
-- text          the source's own words, up to 4,000 characters, contact details stripped
-- url           the page a person opens to see the item itself
-- published     the date the source printed, or empty when it printed none
-- date_known    false when the source printed no date
-- observed      the date the item is about, when that differs from published
-- location      the project location it names, as JSON: geo_loc_id, name, latitude and longitude
-- image_urls    for a satellite item, the tile addresses of two years as a JSON list of two lists of nine
-- author        the outlet, agency or account as the source prints it; never an email or a phone number
-- read_on       the day Prism first fetched it
-- public_from   the day the item became public (ADR 0002): the notice's, the ISR's, the article's, the case's date,
--               or the mosaic's year end
CREATE TABLE IF NOT EXISTS strata.ops.research_items (
  evidence_id STRING NOT NULL,
  run_id STRING NOT NULL,
  project_id STRING NOT NULL,
  source_key STRING NOT NULL,
  kind STRING NOT NULL,
  source STRING NOT NULL,
  title STRING NOT NULL,
  text STRING NOT NULL,
  url STRING NOT NULL,
  published DATE,
  date_known BOOLEAN NOT NULL,
  observed DATE,
  location STRING,
  image_urls STRING NOT NULL,
  author STRING,
  read_on DATE NOT NULL,
  public_from DATE NOT NULL
)
