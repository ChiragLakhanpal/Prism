#!/usr/bin/env python3
"""The gate's secret scan, with no network: the staged changes and the full history of HEAD.

It looks at every added line for the key shapes Strata's .env.example holds (a Databricks
personal access token, an Azure OpenAI key, an Application Insights connection string)
and a few common others (Azure storage keys, private keys, GitHub tokens). It names the
file and the commit but never prints the key. A line that only looks like a key can carry
the marker `strata-gate: not-a-secret`.

Run: python3 gates/secrets.py
"""

import re
import subprocess
import sys

ALLOW = "strata-gate: not-a-secret"
SECRET_NAME = r"[A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|CONNECTION_STRING)"
SHAPES = [
    ("a Databricks personal access token", r"\bdapi[0-9a-f]{32}(?:-\d+)?\b"),
    ("a secret assigned in an environment file",
     rf"^\s*(?:export\s+)?{SECRET_NAME}\s*[:=]\s*['\"]?[A-Za-z0-9_\-+/=.:;]{{16,}}['\"]?\s*(?:#.*)?$"),
    ("an Application Insights connection string",
     r"InstrumentationKey=[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"),
    ("an Azure storage or service key", r"(?:AccountKey|SharedAccessKey)=[A-Za-z0-9+/]{30,}={0,2}"),
    ("an Azure AI services key", r"\b[A-Za-z0-9]{52}JQQJ99[A-Za-z0-9][A-L][A-Za-z0-9]{23}\b"),
    ("a private key", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
    ("a GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})\b"),
]
FINDER = re.compile("|".join(f"(?P<s{i}>{pattern})" for i, (_, pattern) in enumerate(SHAPES)))
COMMIT_MARK = "\x01"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def shape_of(line):
    """The name of the key shape a line holds, or None."""
    if ALLOW in line:
        return None
    match = FINDER.search(line)
    return SHAPES[int(match.lastgroup[1:])][0] if match else None


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, errors="replace").stdout


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
    if not git("rev-parse", "--verify", "-q", "HEAD").strip():
        return ""
    return git("log", "-p", "--no-color", "--no-ext-diff", "-U0", f"--format={COMMIT_MARK}%h \"%s\"", "HEAD")


def main():
    found = [f"{path}, line {number}, in the staged changes: {shape}"
             for _, path, number, shape in scan_patch(staged_patch())]
    found += [f"{path}, added by commit {commit}: {shape}"
              for commit, path, _, shape in scan_patch(history_patch())]
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
