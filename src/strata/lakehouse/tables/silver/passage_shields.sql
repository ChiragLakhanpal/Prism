-- What Prompt Shields found in each passage when it was ingested (src/strata/knowledge/shields.py).
-- A passage is scanned once for each text and shield: a row here means its text, with its header,
-- was scanned, and a run scans only texts with no row. A passage in which an attack was found is
-- kept, counted in strata.ops.data_readiness (passages_prompt_shields_hit) and left out of search
-- with its reason.
--
-- text_hash        SHA-256 of the passage's header and text (silver.passages.text_hash)
-- shield           the shield that scanned it: Prompt Shields, or the offline stand-in
-- attack_detected  whether it found a prompt attack
-- detail           what it found, as a sentence; empty when it found nothing
-- scanned_at       when, in UTC
-- public_from      the passage's public date when it was first scanned (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.passage_shields (
  text_hash STRING NOT NULL,
  shield STRING NOT NULL,
  attack_detected BOOLEAN NOT NULL,
  detail STRING,
  scanned_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
