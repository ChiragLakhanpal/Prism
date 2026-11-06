#!/usr/bin/env python3
"""Strata's PreToolUse guard: CLAUDE.md rules 5, 6, 7 and 10, made deterministic.

Claude Code runs this before every Bash, Read, Grep, Write and Edit call. Exit
code 2 blocks the call and shows Claude the reason. Blocked:

- destructive SQL: DROP, TRUNCATE TABLE, DROP COLUMN, DELETE without WHERE
- deleting Databricks or Azure resources, and outward-facing GitHub actions
- git commands that push, change main, skip the gate, or throw work away
- rm on the repo, its key folders, a worktree, the tracker, or anything outside the repo
- writing outside the repo, its worktrees, temp folders and ~/.claude (fairshare is read-only here)
- reading, printing or copying .env

`python3 .claude/hooks/guard.py --env-keys` lists which .env keys are set, never their values.
Tests: `python3 .claude/hooks/test_guard.py`.
"""

import functools
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

PUSH = "Pushing waits for the user's go-ahead (CLAUDE.md rule 10). Ask the user; they push from their own terminal."
MAIN = ("main changes only with the user's go-ahead (CLAUDE.md rule 10). Work on build/strata or a ticket "
        "branch, and ask the user to merge into main.")
GATE = "The gate runs before every commit (CLAUDE.md rule 6). Fix what it reports instead of skipping it."
DISCARD = "This throws away work that can't be recovered. Find a way that keeps it, or ask the user."
HISTORY = "Rewriting history waits for the user's go-ahead."
SQL = ("Destructive SQL is blocked (CLAUDE.md rule 5). Change a table with CREATE OR REPLACE; "
       "remove rows only with DELETE ... WHERE.")
CLOUD = ("Deleting cloud resources waits for the user's go-ahead: the Databricks workspace is shared "
         "with fairshare, and the Azure resources hold the agent and the models.")
OUTWARD = "Outward-facing GitHub actions wait for the user's go-ahead (CLAUDE.md rule 10)."
ENV = ("Secrets stay out of the transcript (CLAUDE.md rule 7). To see which keys are set, run "
       "`python3 .claude/hooks/guard.py --env-keys`; to add a non-secret value, append it with `>> .env`.")
RM = "rm on {} is blocked: it is the repo, a key folder, a worktree, the tracker, or outside the repo."
OUTSIDE = ("Agents write only inside this repo, its worktrees, temp folders and ~/.claude; "
           "fairshare and the rest of the machine are read-only here.")

ENV_PATH = re.compile(r"(?<![\w.-])\.env(?:\.(?!example\b)[\w-]+)?(?![\w.-])")
ENV_SAFE = {"source", ".", "ls", "test", "[", "stat", "touch", "chmod", "wc"}

SQL_RULES = [
    re.compile(r"\bdrop\s+(?:table|schema|database|catalog|view|materialized\s+view|volume|function|column)\b", re.I),
    re.compile(r"\btruncate\s+table\b", re.I),
]
DELETE_FROM = re.compile(r"\bdelete\s+from\s+[\w.`\"{}$\[\]]+", re.I)
WHERE = re.compile(r"\bwhere\b", re.I)
SQL_QUIET = {"git", "echo", "printf", "gh", "grep", "egrep", "rg"}
SCANNED = (".sql", ".py", ".ipynb", ".sh", ".yml", ".yaml", ".toml", ".json", ".ts", ".tsx", ".js")
EXEMPT_DIRS = {"tests", "test", "__tests__", "benchmark", "benchmarks", "evals"}

SEPARATOR_CHARS = set(";|&()")
REDIRECT_CHARS = set("<>&|")
WRAPPERS = {"sudo", "command", "nohup", "time", "env", "exec", "builtin", "nice", "caffeinate"}
SHELLS = {"bash", "sh", "zsh", "dash"}
WRITERS = {"cp", "mv", "rsync", "install", "ln"}                     # the last path is the destination
TOUCHERS = {"tee", "touch", "mkdir", "chmod", "chown", "truncate"}  # every path is written
# Runners execute the command that follows them: name -> (subcommands that start it, options taking a value)
RUNNERS = {
    "uv": ({"run"}, {"--env-file", "--with", "--python", "-p", "--project", "--directory", "--package", "--extra",
                     "--group", "--index", "--index-url"}),
    "poetry": ({"run"}, set()),
    "pnpm": ({"exec", "dlx"}, set()),
    "npx": (None, {"-p", "--package"}),
    "uvx": (None, {"--from", "--with", "--python", "-p"}),
    "bunx": (None, set()),
    "timeout": (None, {"-s", "--signal", "-k", "--kill-after"}),
    "xargs": (None, {"-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a"}),
}

GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
COMMIT_VALUE_OPTS = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--author", "--date", "--template",
                     "--reuse-message", "--reedit-message", "--fixup", "--squash", "--trailer", "--cleanup"}
MAIN_REFS = {"main", "refs/heads/main", "heads/main"}
MAIN_CHANGERS = {"commit", "merge", "rebase", "reset", "cherry-pick", "revert", "am", "pull"}
WIPE_PATHS = {".", "./", ":/", ":/*", "*", ":(top)"}

KEY_DIRS = (".git", ".scratch", ".claude", ".claude/agents", ".claude/hooks", ".claude/skills",
            ".claude/worktrees", ".githooks", "docs", "docs/adr", "docs/agents")
TEMP_ROOTS = tuple(sorted({os.path.realpath(p) + os.sep for p in
                           ("/tmp", "/private/tmp", "/private/var/folders", tempfile.gettempdir())}))

GH_OUTWARD = {("repo", "create"), ("repo", "delete"), ("repo", "edit"), ("repo", "rename"), ("repo", "archive"),
              ("pr", "create"), ("pr", "merge"), ("pr", "close"), ("pr", "ready"), ("issue", "create"),
              ("release", "create"), ("release", "delete"), ("secret", "set"), ("secret", "delete"),
              ("variable", "set")}


class Blocked(Exception):
    pass


def block(reason):
    raise Blocked(reason)


# ── Paths and git state ──────────────────────────────────────────────────

def project_dir():
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR")
                            or os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))


def resolve(cwd, path):
    return os.path.realpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(path))))


def _git(cwd, *args):
    try:
        done = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
        return done.returncode, done.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def _branch(cwd):
    return _git(cwd, "symbolic-ref", "--short", "-q", "HEAD")[1]


def _has_commits(cwd):
    return _git(cwd, "rev-parse", "--verify", "-q", "HEAD")[0] == 0


def _toplevel(cwd):
    code, out = _git(cwd, "rev-parse", "--show-toplevel")
    return os.path.realpath(out) if code == 0 and out else ""


def _main_checkout(cwd):
    code, out = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.dirname(out) if code == 0 and out else project_dir()


@functools.lru_cache(maxsize=None)
def _write_roots(cwd):
    home = os.path.expanduser("~")
    roots = {project_dir(), _toplevel(cwd), os.path.join(home, ".claude"), os.path.join(home, ".diagram-design")}
    return tuple(os.path.realpath(r) + os.sep for r in roots if r) + TEMP_ROOTS + ("/dev/",)


def _writable(path, cwd):
    target = os.path.realpath(os.path.join(cwd, os.path.expandvars(os.path.expanduser(path))))
    return (target + os.sep).startswith(_write_roots(cwd))


# ── Shell parsing ────────────────────────────────────────────────────────

def _normalize(command):
    """Turn unquoted newlines into ';' and drop comments, so each line is its own command."""
    out, quote, escaped, comment, prev = [], None, False, False, " "
    for ch in command:
        if comment:
            if ch == "\n":
                comment = False
                out.append(";")
            continue
        if escaped:
            escaped = False
        elif ch == "\\" and quote != "'":
            escaped = True
        elif quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (prev.isspace() or prev in ";&|("):
            comment = True
            continue
        elif ch == "\n":
            ch = ";"
        out.append(ch)
        prev = ch
    return "".join(out)


def simple_commands(command):
    lexer = shlex.shlex(_normalize(command), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    words = []
    for token in lexer:
        if token and set(token) <= SEPARATOR_CHARS:
            if words:
                yield words
            words = []
        else:
            words.append(token)
    if words:
        yield words


def parse(words):
    """Split a simple command into argv and redirects, dropping env assignments and wrappers."""
    argv, redirects, i = [], [], 0
    while i < len(words):
        word = words[i]
        if word and set(word) <= REDIRECT_CHARS and ("<" in word or ">" in word):
            redirects.append((word, words[i + 1] if i + 1 < len(words) else ""))
            i += 2
            continue
        argv.append(word)
        i += 1
    while argv and (re.fullmatch(r"[A-Za-z_]\w*=.*", argv[0], re.S) or argv[0] in WRAPPERS):
        wrapper = argv.pop(0) in WRAPPERS
        while wrapper and argv and argv[0].startswith("-"):
            argv.pop(0)
    return argv, redirects


def _short_has(arg, letter):
    return bool(re.fullmatch(r"-[A-Za-z]+", arg)) and letter in arg[1:]


# ── Checks ───────────────────────────────────────────────────────────────

def destructive_sql(text):
    if any(rule.search(text) for rule in SQL_RULES):
        return True
    for match in DELETE_FROM.finditer(text):
        statement = text[match.end():match.end() + 400].split(";", 1)[0]
        if not WHERE.search(statement):
            return True
    return False


def check_bash(command, cwd):
    try:
        commands = list(simple_commands(command))
    except ValueError:  # unbalanced quotes: judge the raw text
        if re.search(r"\bgit\b[^;&|]*\bpush\b", command):
            block(PUSH)
        if "--no-verify" in command:
            block(GATE)
        if destructive_sql(command):
            block(SQL)
        if ENV_PATH.search(command):
            block(ENV)
        return
    for words in commands:
        cwd = check_words(words, cwd)


def check_words(words, cwd):
    argv, redirects = parse(words)
    check_env(argv, redirects)
    for op, target in redirects:
        if ">" in op and target and not target.isdigit() and not _writable(target, cwd):
            block(OUTSIDE)
    return check_argv(argv, cwd) if argv else cwd


def check_argv(argv, cwd):
    name = os.path.basename(argv[0])
    if name in ("cd", "pushd"):
        return resolve(cwd, argv[1]) if len(argv) > 1 else os.path.expanduser("~")
    if name in RUNNERS:
        inner = _inner_command(argv)
        if inner:
            check_argv(inner, cwd)
        return cwd
    if name in WRITERS or name in TOUCHERS or (name == "sed" and any(a.startswith("-i") or a == "--in-place"
                                                                        for a in argv[1:])):
        _check_destinations(name, argv, cwd)
    if name in SHELLS:
        for i, arg in enumerate(argv[1:-1], 1):
            if _short_has(arg, "c"):
                check_bash(argv[i + 1], cwd)
                break
    elif name == "eval":
        check_bash(" ".join(argv[1:]), cwd)
    elif name == "git":
        check_git(argv, cwd)
    elif name == "rm":
        check_rm(argv, cwd)
    elif name == "databricks":
        check_cloud(argv, {"delete", "destroy", "rm", "purge"})
    elif name == "az":
        check_cloud(argv, {"delete", "purge"})
    elif name == "gh":
        check_gh(argv)
    elif name == "curl":
        check_curl(argv)
    if name not in SQL_QUIET and destructive_sql(" ".join(argv)):
        block(SQL)
    return cwd


def _check_destinations(name, argv, cwd):
    paths = [a for a in argv[1:] if not a.startswith("-")]
    if name in WRITERS:
        paths = paths[-1:] if len(paths) > 1 else []
    elif name == "sed":
        paths = paths[1:]  # the first is the script
    for path in paths:
        if not _writable(path, cwd):
            block(OUTSIDE)


def _inner_command(argv):
    """The command a runner such as `uv run`, `npx` or `xargs` will execute."""
    name = os.path.basename(argv[0])
    subcommands, value_options = RUNNERS[name]
    i = 1
    if subcommands is not None:
        if len(argv) < 2 or argv[1] not in subcommands:
            return []
        i = 2
    while i < len(argv) and argv[i].startswith("-"):
        i += 2 if argv[i] in value_options else 1
    if name == "timeout":
        i += 1  # the duration
    return argv[i:]


def check_env(argv, redirects):
    for op, target in redirects:
        if ENV_PATH.search(target) and op != ">>":
            block(ENV)
    if not argv or os.path.basename(argv[0]) in ENV_SAFE:
        return
    previous = ""
    for arg in argv[1:]:
        if ENV_PATH.search(arg) and previous != "--env-file" and not arg.startswith("--env-file="):
            block(ENV)
        previous = arg


def check_git(argv, cwd):
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        option = argv[i]
        value = argv[i + 1] if i + 1 < len(argv) else ""
        if option == "-C":
            cwd = resolve(cwd, value)
        if option == "-c" and value.lower().startswith("core.hookspath"):
            block(GATE)
        i += 2 if option in GIT_VALUE_OPTS else 1
    if i >= len(argv):
        return
    sub, args = argv[i], argv[i + 1:]
    flags = set(args)

    if "--no-verify" in flags or (sub == "commit" and _commit_skips_gate(args)):
        block(GATE)
    if sub == "config":
        _check_hooks_path(args)
    if sub == "push":
        block(PUSH)
    if sub in ("filter-branch", "filter-repo") or (sub == "reflog" and flags & {"expire", "delete"}):
        block(HISTORY)

    if sub == "reset" and "--hard" in flags:
        block(DISCARD)
    if sub == "clean" and ("--force" in flags or any(_short_has(a, "f") for a in args)):
        block(DISCARD)
    if sub == "stash" and args[:1] in (["drop"], ["clear"]):
        block(DISCARD)
    if sub in ("checkout", "switch") and flags & {"-f", "--force", "--discard-changes"}:
        block(DISCARD)
    if sub in ("checkout", "restore"):
        staged_only = flags & {"--staged", "-S"} and not flags & {"--worktree", "-W"}
        if not staged_only and _pathspecs(args) & WIPE_PATHS:
            block(DISCARD)

    if sub == "branch":
        if flags & MAIN_REFS and flags & {"-f", "--force", "-m", "-M", "--move", "-d", "-D", "--delete", "-C"}:
            block(MAIN)
        if any(_short_has(a, "D") for a in args) or (flags & {"-d", "--delete"} and flags & {"-f", "--force"}):
            block(DISCARD)
    if sub in ("checkout", "switch") and flags & {"-B", "-C", "--force-create"} and flags & MAIN_REFS:
        block(MAIN)
    if sub == "update-ref" and ("-d" in flags or flags & MAIN_REFS):
        block(MAIN)
    if sub == "rebase" and _rebase_target(args) in MAIN_REFS:
        block(MAIN)
    if sub in MAIN_CHANGERS and _branch(cwd) == "main":
        if sub == "commit" and not _has_commits(cwd):
            return  # the first commit on main
        if flags & {"--abort", "--quit"} or (sub == "reset" and _only_unstages(args)):
            return
        block(MAIN)


def _commit_skips_gate(args):
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in COMMIT_VALUE_OPTS:
            skip = True
        elif re.fullmatch(r"-[A-Za-z]+", arg):
            for j, letter in enumerate(arg[1:], 1):
                if letter == "n":
                    return True
                if letter in "mFCct":
                    skip = j == len(arg) - 1
                    break
    return False


def _check_hooks_path(args):
    lowered = [a.lower() for a in args]
    if "core.hookspath" not in lowered:
        return
    if {"--unset", "--unset-all", "--remove-section"} & set(args):
        block(GATE)
    k = lowered.index("core.hookspath")
    if k + 1 < len(args) and args[k + 1].rstrip("/") != ".githooks":
        block(GATE)


def _pathspecs(args):
    if "--" in args:
        return set(args[args.index("--") + 1:])
    return {a for a in args if not a.startswith("-")}


def _rebase_target(args):
    positional, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg in ("--onto", "-s", "--strategy", "-X", "--strategy-option", "-x", "--exec"):
            skip = True
        elif not arg.startswith("-"):
            positional.append(arg)
    return positional[1] if len(positional) > 1 else None


def _only_unstages(args):
    head = args[:args.index("--")] if "--" in args else args
    return all(a in ("-q", "--quiet", "--mixed", "HEAD") for a in head)


def check_rm(argv, cwd):
    recursive = any(a == "--recursive" or _short_has(a, "r") or _short_has(a, "R") for a in argv[1:])
    roots = {r for r in (project_dir(), _toplevel(cwd)) if r}
    for target in (a for a in argv[1:] if not a.startswith("-")):
        expanded = os.path.expandvars(os.path.expanduser(target))
        if "$" in expanded:
            block(RM.format(target))
        if os.path.basename(expanded) in ("*", ".*"):
            expanded = os.path.dirname(expanded) or "."
        path = os.path.realpath(os.path.join(cwd, expanded))
        inside = any(path.startswith(r + os.sep) for r in roots)
        if not inside and not path.startswith(TEMP_ROOTS):
            block(RM.format(target))
        for root in roots:
            kept = [os.path.join(root, d) for d in (".git", ".scratch")]
            if any(path == k or path.startswith(k + os.sep) for k in kept):
                block(RM.format(target))
            if recursive and (path in {os.path.join(root, d) for d in KEY_DIRS}
                              or os.path.dirname(path) == os.path.join(root, ".claude", "worktrees")):
                block(RM.format(target))


def check_cloud(argv, deleting):
    lowered = {a.lower() for a in argv[1:]}
    if lowered & deleting or any(a.startswith("delete-") for a in lowered):
        block(CLOUD)


def check_gh(argv):
    if tuple(argv[1:3]) in GH_OUTWARD:
        block(OUTWARD)
    if argv[1:2] == ["api"]:
        args = argv[2:]
        if {"-f", "-F", "--field", "--raw-field", "--input"} & set(args) or _method(args) not in ("", "GET"):
            block(OUTWARD)


def check_curl(argv):
    if _method(argv[1:]) == "DELETE":
        block(CLOUD)


def _method(args):
    for i, arg in enumerate(args):
        if arg in ("-X", "--request", "--method") and i + 1 < len(args):
            return args[i + 1].upper()
        if arg.startswith(("--request=", "--method=")):
            return arg.split("=", 1)[1].upper()
        if arg.startswith("-X") and len(arg) > 2:
            return arg[2:].upper()
    return ""


def check_file(tool, data, cwd):
    path = data.get("file_path") or data.get("notebook_path") or data.get("path") or ""
    if ENV_PATH.fullmatch(os.path.basename(path)):
        block(ENV)
    if tool in ("Read", "Grep"):
        return
    if path and not _writable(path, cwd):
        block(OUTSIDE)
    if not _scanned(path):
        return
    text = data.get("content") or data.get("new_string") or data.get("new_source") or ""
    text += "".join(edit.get("new_string", "") for edit in data.get("edits") or [])
    if destructive_sql(text):
        block(SQL)


def _scanned(path):
    if not path.endswith(SCANNED):
        return False
    parts = os.path.normpath(path).split(os.sep)
    name = parts[-1]
    if EXEMPT_DIRS & set(parts[:-1]) or ("/.claude/hooks/" in "/" + "/".join(parts)):
        return False
    return not (name.startswith("test_") or name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")))


# ── Entry points ─────────────────────────────────────────────────────────

def env_keys():
    """Print each key in .env as set, empty or missing, compared with .env.example. Never values."""
    root = _main_checkout(os.getcwd())

    def read(name):
        found = {}
        path = os.path.join(root, name)
        if os.path.exists(path):
            with open(path) as handle:
                for line in handle:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        found[key.replace("export ", "", 1).strip()] = bool(value.strip().strip("'\""))
        return found

    actual, expected = read(".env"), read(".env.example")
    if not actual:
        print(".env is missing or empty; .env.example lists the keys it needs.")
    for key in list(expected) + [k for k in actual if k not in expected]:
        print(f"{key}: {'missing' if key not in actual else 'set' if actual[key] else 'empty'}")
    return 0


def main():
    if sys.argv[1:] == ["--env-keys"]:
        return env_keys()
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = event.get("tool_name", "")
    data = event.get("tool_input") or {}
    cwd = event.get("cwd") or os.getcwd()
    try:
        if tool == "Bash":
            check_bash(data.get("command", ""), cwd)
        elif tool in ("Read", "Grep", "Write", "Edit", "MultiEdit", "NotebookEdit"):
            check_file(tool, data, cwd)
    except Blocked as reason:
        print(f"Blocked by .claude/hooks/guard.py: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
