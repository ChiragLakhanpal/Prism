-- Each passage's vector, from its short header, a line break and its text (src/strata/knowledge/embed.py).
-- A text is embedded once for each model: a run embeds only the texts the model has no row for, so a
-- passage that did not change is never embedded again. strata.gold.passage carries the vector to the
-- AI Search index.
--
-- text_hash    SHA-256 of what was embedded (silver.passages.text_hash)
-- model        the deployment that made it, such as text-embedding-3-large, or the offline stand-in
-- dimensions   the vector's size: config/models.toml's embed dimensions
-- embedding    the vector
-- embedded_at  when, in UTC
-- public_from  the passage's public date when it was first embedded (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.passage_embeddings (
  text_hash STRING NOT NULL,
  model STRING NOT NULL,
  dimensions INT NOT NULL,
  embedding ARRAY<FLOAT> NOT NULL,
  embedded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
