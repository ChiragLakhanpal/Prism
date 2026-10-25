-- What became of each group of passage reports (ticket 32; docs/PLAN.md section 11, "Feedback"). A group is
-- one passage and one kind of question, and one decision covers every report waiting in it. Each act is a
-- new row and the latest row of a group gives its state, so nothing changes or leaves: reopening a decided
-- group writes a row that puts it back in the queue and gives the passage its earlier ranking.
--
-- A passage is ranked lower for its kind of question while its group's latest act is accepted,
-- accepted_by_agreement or left_lower. It is never hidden: search still shows it when it is the only
-- source (strata.knowledge.retrieval.demotion). Only these reviewed labels train anything, and no
-- evaluation set ever takes one (strata.knowledge.retrieval.labels).
--
-- decision_id     the act's id
-- group_id        the group: its passage and kind of question, as one id
-- passage_id      the passage
-- query_kind      the kind of question it is ranked lower for (config/retrieval.toml)
-- act             accepted (a passage reviewer chose "Rank it lower"), declined ("Keep its ranking"),
--                 accepted_by_agreement (at scale, the weekly run's silver label), left_lower or restored (a
--                 reviewer's answer to an audit sample), audit (an agreement picked for a reviewer to
--                 check), reopened (back in the queue, with the earlier ranking), or routed (at scale, sent
--                 to a person, with why in reason)
-- reason          the reviewer's reason, required for every act a person takes, or why the run routed it
-- reviewer_email  the passage reviewer who acted, or empty for the weekly run
-- reviewer_name   their name in the roles file
-- report_ids      the reports the act covers, as a JSON list
-- agreeing        how many different people made the same report, for an agreement
-- label_weight    the label's weight from its reporters' reliability (Dawid and Skene), a tool column
-- expected_state  the state the reviewer saw when they acted
-- decided_at      when, in UTC
-- public_from     the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.label_decisions (
  decision_id STRING NOT NULL,
  group_id STRING NOT NULL,
  passage_id STRING NOT NULL,
  query_kind STRING NOT NULL,
  act STRING NOT NULL,
  reason STRING,
  reviewer_email STRING,
  reviewer_name STRING,
  report_ids STRING NOT NULL,
  agreeing INT,
  label_weight DOUBLE,
  expected_state STRING,
  decided_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
