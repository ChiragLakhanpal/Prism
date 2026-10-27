#!/usr/bin/env python3
"""The gate's secret scan. It reads the staged changes and the full history of HEAD, with no network.
During a merge it also reads the history of the branch the merge brings in.

It checks every added line for the key shapes that Strata's .env.example holds. Those are a
Databricks personal access token, an Azure OpenAI key and an Application Insights connection
string. It also checks a few other common shapes, such as Azure storage keys, private keys,
GitHub tokens and a key assigned in code. It names the file and the commit but never prints
the key. A line that only looks like a key can carry the marker `strata-gate: not-a-secret`.

This file is not named secrets.py, because that name would hide Python's own `secrets`
module from every script in gates/. A test in tests/test_gate.py keeps it that way.

Run it with this command:

    python3 gates/secret_scan.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ALLOW = "strata-gate: not-a-secret"
SECRET_NAME = r"[A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|CONNECTION_STRING)"
# Most specific first: a line is reported as the first shape it matches.
SHAPES = [
    ("a Databricks personal access token", r"\bdapi[0-9a-f]{32}(?:-\d+)?\b"),
    ("an Application Insights connection string",
     r"InstrumentationKey=[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"),
    ("an Azure storage or service key", r"(?:AccountKey|SharedAccessKey)=[A-Za-z0-9+/]{30,}={0,2}"),
    ("an Azure AI services key", r"\b[A-Za-z0-9]{52}JQQJ99[A-Za-z0-9][A-L][A-Za-z0-9]{23}\b"),
    ("a private key", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
    ("a GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})\b"),
    ("a key assigned in code",
     r"\b(?i:api_?key|access_?token|client_?secret|secret|password)['\"]?\s*[:=]\s*['\"][A-Za-z0-9_\-+/=.]{20,}['\"]"),
    ("a secret assigned in an environment file",
     rf"^\s*(?:export\s+)?{SECRET_NAME}\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/=.:;]{{16,}}['\"]?\s*(?:#.*)?$"),
]
COMPILED = [(name, re.compile(pattern)) for name, pattern in SHAPES]
FINDER = re.compile("|".join(f"(?:{pattern})" for _, pattern in SHAPES))
COMMIT_MARK = "\x01"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def shape_of(line):
    """The name of the most specific key shape a line holds, or None."""
    if ALLOW in line or not FINDER.search(line):
        return None
    return next(name for name, pattern in COMPILED if pattern.search(line))


def git(*args, check=True):
    """Git's output. When git fails and check is true, raise, so the scan never reads a failure as no keys."""
    return subprocess.run(["git", *args], capture_output=True, text=True, errors="replace", check=check).stdout


def scan_patch(patch):
    """Yield (commit line, path, line number, shape) for each added line that holds a key."""
    commit, path, number = "", "", 0
    for line in patch.splitlines():
        if line.startswith(COMMIT_MARK):
            commit, path = line[1:], ""
        elif line.startswith("+++ "):
            name = line[4:].rstrip("\t").strip('"')
            path = name[2:] if name.startswith("b/") else ""
        elif line.startswith("@@"):
            hunk = HUNK.match(line)
            number = int(hunk.group(1)) if hunk else 0
        elif line.startswith("+") and path:
            shape = shape_of(line[1:])
            if shape:
                yield commit, path, number, shape
            number += 1


def staged_patch():
    return git("diff", "--cached", "--no-color", "--no-ext-diff", "-U0")


def is_commit(name):
    return bool(git("rev-parse", "--verify", "-q", f"{name}^{{commit}}", check=False).strip())


def merge_heads():
    """The commits that a merge in progress brings in, so the scan reads their history as well as HEAD's.

    `git commit` after `git merge --no-commit` finds them in MERGE_HEAD. A plain `git merge` runs
    pre-merge-commit before it writes MERGE_HEAD, and names what it merges in GIT_REFLOG_ACTION,
    such as "merge strata/57-gate-fixes" (ticket 01's verification, V1).
    """
    heads = []
    merge_head = Path(git("rev-parse", "--git-path", "MERGE_HEAD").strip())
    if merge_head.is_file():
        heads += merge_head.read_text().split()
    action = os.environ.get("GIT_REFLOG_ACTION", "").split()
    if action[:1] == ["merge"]:
        heads += [name for name in action[1:] if is_commit(name)]
    return heads


def history_patch(heads=()):
    """The history of HEAD, and of heads, the commits a merge in progress brings in."""
    if not is_commit("HEAD"):  # a repo with no commits yet
        return ""
    return git("log", "-p", "--no-color", "--no-ext-diff", "-U0", f"--format={COMMIT_MARK}%h \"%s\"", "HEAD",
               *heads, "--")


def main():
    try:
        heads = merge_heads()
        staged, history = staged_patch(), history_patch(heads)
    except subprocess.CalledProcessError as failed:
        print("The secret scan could not read the changes from git, so it cannot tell whether they hold a key. "
              f"Git said this: {failed.stderr.strip()}")
        return 1
    found = [f"{path}, line {number}, in the staged changes: {shape}"
             for _, path, number, shape in scan_patch(staged)]
    found += [f"{path}, added by commit {commit}: {shape}"
              for commit, path, _, shape in scan_patch(history)]
    if not found:
        print("The secret scan found no keys in the staged changes or the history"
              f"{', or in the branch the merge brings in' if heads else ''}.")
        return 0
    print("The secret scan found what looks like a key. It does not print the key itself.")
    for line in found:
        print(f"  {line}")
    print("Remove the key, and rotate it if it is real. Secrets belong in .env, which git ignores "
          "(CLAUDE.md rule 7). A key in an earlier commit stays in the history until that history "
          f"is rewritten, which waits for the user's go-ahead. If a line only looks like a key, add "
          f"the marker \"{ALLOW}\" to it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
