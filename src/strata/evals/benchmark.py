"""The benchmark file, evals/benchmark.yaml: what it must hold, read once (spec, "Ten single places", item 9).

The file holds four kinds of question (docs/PLAN.md section 10):

- sql: a structured question with ground-truth SQL, answered by a registry tool such as check_plan, or by
  ask_genie, whose ground-truth SQL is the expected answer itself;
- documents: a question whose answer cites passages, with the citations it must carry (cites);
- estimates: a question about a range or a count, with the range or the abstention it must give;
- refusals: the must-refuse set, one question per refusal key in src/strata/agent/refusals.py.

problems() says what the file lacks: a registry tool with no question of its own (CLAUDE.md rule 4), a refusal
key with no must-refuse question, fewer than [benchmark] min_questions_per_kind questions of a kind, and questions
written wrong. The offline gate runs it (tests/test_benchmark.py), and so does the full gate before it asks
anything, so a question added to the file runs in the next full gate with no other change.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

from strata.config import Tool, load_thresholds, load_tools

ROOT = Path(__file__).resolve().parents[3]
BENCHMARK = ROOT / "evals" / "benchmark.yaml"
KINDS = ("sql", "documents", "estimates", "refusals")
COUNTED = ("sql", "documents", "estimates")  # the kinds with a minimum count; refusals go by key instead


def load(path: Path = BENCHMARK) -> list[dict]:
    """Every question in the file, in order. libyaml's loader reads it six times faster than PyYAML's own."""
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    return list(yaml.load(Path(path).read_text(), Loader=loader)["questions"])


def counts(questions: list[dict]) -> dict[str, int]:
    """How many questions of each kind the file holds."""
    found = Counter(question.get("kind") for question in questions)
    return {kind: found[kind] for kind in KINDS}


def _listed(words: list[str]) -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def problems(questions: list[dict], tools: dict[str, Tool] | None = None, refusals: tuple[str, ...] | None = None,
             minimum: int | None = None, root: Path = ROOT) -> list[str]:
    """What the benchmark file lacks or holds wrong, one sentence each. Empty when it is complete."""
    from strata.agent.refusals import REFUSALS

    tools = load_tools() if tools is None else tools
    refusals = REFUSALS if refusals is None else refusals
    minimum = int(load_thresholds().value("benchmark.min_questions_per_kind")) if minimum is None else minimum
    found: list[str] = []
    by_id: dict[str, dict] = {}
    for question in questions:
        qid = question.get("id")
        if qid in by_id:
            found.append(f"Two questions have the id {qid}.")
        by_id[qid] = question
        if question.get("kind") not in KINDS:
            found.append(f"{qid} is of kind {question.get('kind')}. The kinds are {_listed(list(KINDS))}.")
        if not str(question.get("question") or "").strip():
            found.append(f"{qid} has no question.")
        if "expected" not in question:
            found.append(f"{qid} has no expected answer.")
        if question.get("tool") and question["tool"] not in tools:
            found.append(f"{qid} asks the tool {question['tool']}, which config/tools.toml does not hold.")
        if question.get("ground_truth") and not (root / question["ground_truth"]).is_file():
            found.append(f"{qid} names the ground-truth SQL {question['ground_truth']}, which does not exist.")
        if question.get("tool") == "ask_genie" and not question.get("ground_truth"):
            found.append(f"{qid} asks Genie, so its expected answer is its ground-truth SQL, which it does not name.")
        if question.get("kind") == "refusals":
            expected = question.get("expected") or {}
            if expected.get("must_refuse") is not True or expected.get("refusal") not in refusals:
                found.append(f"{qid} is a must-refuse question, so it needs must_refuse: true and a refusal key "
                             f"from src/strata/agent/refusals.py.")
    for name, tool in tools.items():
        named = by_id.get(tool.benchmark)
        if named is None:
            found.append(f"The tool {name} names the question {tool.benchmark}, which evals/benchmark.yaml does not "
                         "hold. Add its question in the same change (CLAUDE.md rule 4).")
        elif named.get("tool") != name:
            found.append(f"The tool {name} names the question {tool.benchmark}, which asks {named.get('tool')} "
                         "instead. Each tool needs a question of its own (CLAUDE.md rule 4).")
    asked = {(question.get("expected") or {}).get("refusal") for question in questions
             if question.get("kind") == "refusals" and "path" not in question}
    found += [f"The refusal {key} has no must-refuse question." for key in refusals if key not in asked]
    held = counts(questions)
    short = [kind for kind in COUNTED if held[kind] < minimum]
    if short:
        found.append(f"The benchmark file holds {_listed([f'{held[kind]} {kind} questions' for kind in short])}, "
                     f"and it needs at least {minimum} of each.")
    return found
