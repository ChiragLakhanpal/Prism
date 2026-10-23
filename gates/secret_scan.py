#!/usr/bin/env python3
"""The gate's secret scan. It reads the staged changes and the full history of HEAD, with no network.

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

import re
import subprocess
import sys

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


def history_patch():
    if not git("rev-parse", "--verify", "-q", "HEAD", check=False).strip():  # a repo with no commits yet
        return ""
    return git("log", "-p", "--no-color", "--no-ext-diff", "-U0", f"--format={COMMIT_MARK}%h \"%s\"", "HEAD")


def main():
    try:
        staged, history = staged_patch(), history_patch()
    except subprocess.CalledProcessError as failed:
        print("The secret scan could not read the changes from git, so it cannot tell whether they hold a key. "
              f"Git said this: {failed.stderr.strip()}")
        return 1
    found = [f"{path}, line {number}, in the staged changes: {shape}"
             for _, path, number, shape in scan_patch(staged)]
    found += [f"{path}, added by commit {commit}: {shape}"
              for commit, path, _, shape in scan_patch(history)]
    if not found:
        print("The secret scan found no keys in the staged changes or the history.")
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
