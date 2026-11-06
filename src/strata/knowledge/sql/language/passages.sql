-- Every passage the language check can sample: its id, language and words, longest enough for the detector to
-- read (config/thresholds.toml, lang.min_sample_chars). A table's summary is Prism's own words, so it is left out.
SELECT passage_id, language, text
FROM strata.silver.passages
WHERE kind <> 'table_summary' AND length(text) >= :min_chars
ORDER BY passage_id
