# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0"]
# ///
"""Day-one test 5: the Genie conversation API answers as the token's user.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_genie.py --env-file .env

It asks the Genie space in GENIE_SPACE_ID one question with the token from .env, then checks
that the answer completed and that Genie recorded the message under the token's own user. It
writes test 5 in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

NEEDS = ["DATABRICKS_HOST", "GENIE_SPACE_ID"]


def check(genie, env: dict, config: dict) -> Outcome:
    space, question = env["GENIE_SPACE_ID"], config["genie"]["question"]
    try:
        me = genie.user_id()
        reply = genie.ask(space, question)
    except SetupError as error:
        return dayone.not_run(error)
    except ProbeError as error:
        return Outcome("failed", "The Genie conversation API did not answer.", [str(error)])
    evidence = [f"Space {space}, conversation {reply['conversation_id']}, message {reply['message_id']}.",
                f"Question: {question}",
                f"Status: {reply['status']}."]
    if reply.get("answer"):
        evidence.append(f"Answer: {reply['answer']}")
    if reply["status"] != "COMPLETED":
        if reply.get("error"):
            evidence.append(f"Error: {reply['error']}")
        return Outcome("failed", f"Genie did not finish the answer. Its status was {reply['status']}.", evidence)
    if str(reply["user_id"]) != str(me):
        evidence.append(f"The token's user has the ID {me}, and the message has the user ID {reply['user_id']}.")
        return Outcome("failed", "Genie answered, but it recorded the message under another user, not the "
                                 "token's user.", evidence)
    evidence.append(f"The message's user ID, {me}, is the token's user.")
    return Outcome("passed", "Genie answered as the token's user.", evidence)


class CannedGenie:
    """A space that answers as the token's user, for --dry-run."""

    def __init__(self, env: dict, config: dict):
        pass

    def user_id(self):
        return "1001"

    def ask(self, space_id, question):
        return {"status": "COMPLETED", "user_id": "1001", "conversation_id": "dry-run", "message_id": "dry-run",
                "answer": "A canned answer.", "error": None}


def live(env: dict, config: dict):
    from live import LiveGenie
    return LiveGenie(env)


def main(argv: list[str] | None = None, service=None) -> int:
    return dayone.run_probe(5, argv, __doc__, NEEDS, live, CannedGenie, check, service)


if __name__ == "__main__":
    sys.exit(main())
