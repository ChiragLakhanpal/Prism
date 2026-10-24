"""Ask the live judge about the fixture's uncertain pairs of supplier name matching: ticket 19's live check.

Run it from the main checkout, after the gate has built the fixture database:

    uv run --frozen python ops/suppliers/judge_live.py --env-file .env [--record]

It resolves the fixture's supplier rows again on a read-only copy of data/out/fixture.duckdb, exactly
as the nightly job does, but with the live judge (strata.knowledge.suppliers.judge.AzureOpenAIJudge,
the deployment of the role config/models.toml's [supplier_matching] names) in place of the offline
stand-in. It writes nothing to the database. It prints each pair the thresholds sent to the model and
the judgement it gave, and exits 0 when every answer was a judgement in the asked-for shape, 1 when the
model gave none, and 2 when it could not ask. With --record, it saves the first raw answer over
tests/fixtures/azure/supplier_judge.json, marked recorded, for the adapter test to replay.

It needs AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402

NEEDS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
FIXTURE_DB = REPO / "data" / "out" / "fixture.duckdb"
RECORDING = REPO / "tests" / "fixtures" / "azure" / "supplier_judge.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/suppliers/judge_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the Azure OpenAI endpoint and key")
    parser.add_argument("--record", action="store_true", help="save the first raw answer for the adapter test")
    args = parser.parse_args(argv)
    path = Path(args.env_file) if args.env_file else dayone.default_env_path()
    if not path.is_file():
        print(f"There is no env file at {path}. {dayone.WIZARD_FIRST}")
        return 2
    env = dayone.load_env(path)
    missing = dayone.missing_keys(env, list(NEEDS))
    if missing:
        print(f"{path} has no value for {', '.join(missing)}. {dayone.WIZARD_FIRST}")
        return 2
    if not FIXTURE_DB.is_file():
        print(f"There is no fixture database at {FIXTURE_DB}. Run the gate first (.githooks/pre-commit).")
        return 2

    from strata.config import load_models, load_supplier_matching, load_thresholds
    from strata.knowledge.suppliers import judge as judges
    from strata.knowledge.suppliers import resolve
    from strata.lakehouse.engine import DuckDBEngine

    answers = []

    def post(url, headers, body):
        answer = judges.http_post(url, headers, body)
        answers.append(answer)
        return answer

    deployment = load_models()[load_supplier_matching().judge_role].deployment
    live = judges.AzureOpenAIJudge(env["AZURE_OPENAI_ENDPOINT"], env["AZURE_OPENAI_API_KEY"], deployment, post=post)
    with DuckDBEngine.open(FIXTURE_DB, read_only=True) as engine:
        rows = resolve.read_rows(engine)
    try:
        resolution = resolve.resolve(rows, resolve.Routing.from_thresholds(load_thresholds()),
                                     load_supplier_matching(), live)
    except judges.JudgeError as error:
        print(f"I could not ask {live.name}: {error}")
        return 2
    judged = [pair for pair in resolution.pairs if pair.model_judgement is not None]
    print(f"{live.name} judged {len(judged)} pairs that the thresholds sent to the model:")
    for pair in judged:
        verdict = pair.model_judgement
        print(f"  {pair.left.name} | {pair.right.name}: {verdict.decision}, {verdict.confidence:.2f}. {verdict.reason}")
    if not judged:
        return 1
    if args.record:
        RECORDING.write_text(json.dumps({
            "about": "An answer of Azure OpenAI's chat completions from the judge role's deployment, asked whether "
                     "two supplier rows name the same supplier, recorded by ops/suppliers/judge_live.py --record.",
            "recorded": True, "response": answers[0]}, indent=1, ensure_ascii=False) + "\n")
        print(f"I saved the first answer over {RECORDING.relative_to(REPO)}. Review it with git diff and run the gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
