#!/usr/bin/env python3
"""Tests for guard.py, through its real interface: a tool event on stdin, an exit code out.

Run: python3 .claude/hooks/test_guard.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard.py")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run(tool, cwd=REPO, **tool_input):
    event = {"tool_name": tool, "tool_input": tool_input, "cwd": cwd}
    done = subprocess.run([sys.executable, HOOK], input=json.dumps(event), capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": REPO})
    return done.returncode


def bash(command, cwd=REPO):
    return run("Bash", cwd=cwd, command=command)


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   check=True, capture_output=True)


BLOCKED = [
    # pushing and outward-facing actions
    "git push", "git push origin build/strata", "cd docs && git push --force", "git -C . push",
    "bash -c 'git push'", "uv run git push", "timeout 60 git push", "uv run --env-file .env cat .env",
    "gh repo create strata --private --source .", "gh pr create --fill",
    "gh api -X DELETE repos/owner/strata",
    # skipping the gate
    "git commit --no-verify -m 'x'", "git commit -nm 'x'", "git -c core.hooksPath=/dev/null commit -m x",
    "git config core.hooksPath /dev/null", "git config --unset core.hooksPath",
    # throwing work away
    "git reset --hard HEAD~1", "git clean -fd", "git clean -xdf", "git branch -D strata/01-scaffold",
    "git checkout .", "git checkout -- .", "git restore .", "git checkout -f build/strata", "git stash drop",
    "git filter-branch --tree-filter x HEAD",
    # changing main from any branch
    "git branch -f main HEAD~1", "git checkout -B main", "git switch -C main",
    "git update-ref refs/heads/main HEAD", "git rebase build/strata main",
    # rm
    "rm -rf .", "rm -rf /", "rm -rf ~", "rm -rf *", "rm -rf docs", "rm -rf .scratch",
    "rm .scratch/strata/issues/01-scaffold.md", "rm -rf .git", "rm -rf .claude/worktrees/agent-1",
    'rm -rf "$STRATA_UNSET_VARIABLE/x"', "rm -rf ../fairshare", "rm ~/.zshrc",
    # .env
    "cat .env", "head -5 .env", "grep TOKEN .env", "cp .env ../fairshare/.env", "echo x > .env",
    "cat < .env", "git add -f .env", "python3 -c \"print(open('.env').read())\"",
    # writing outside the repo (fairshare is read-only)
    "cp src/strata/db.py ../fairshare/src/db.py", "echo x > ../fairshare/notes.txt",
    "sed -i 's/a/b/' ../fairshare/app.py", "touch ~/Desktop/strata.txt",
    # deleting cloud resources
    "databricks catalogs delete strata", "databricks bundle destroy",
    "databricks fs rm -r dbfs:/Volumes/strata/bronze/raw", "az group delete -n WorldBank-demo",
    "curl -X DELETE https://example.cloud.databricks.com/api/2.1/unity-catalog/tables/strata.gold.x",
    # destructive SQL
    "python3 -c \"spark.sql('drop table strata.gold.contracts')\"",
    "duckdb data/out/strata.duckdb \"DELETE FROM contracts\"",
    "databricks api post /api/2.0/sql/statements --json '{\"statement\": \"TRUNCATE TABLE strata.silver.x\"}'",
    "python3 - <<'EOF'\nspark.sql(\"ALTER TABLE strata.gold.x DROP COLUMN y\")\nEOF",
]

ALLOWED = [
    "git status", "git log --oneline -20 build/strata", "git diff build/strata...strata/01-scaffold",
    "git switch -c build/strata", "git restore --staged .", "git checkout -- web/src/App.tsx",
    "git worktree remove .claude/worktrees/agent-1", "git branch -d strata/01-scaffold",
    "git config core.hooksPath .githooks", "git config --get core.hooksPath",
    "rm -rf web/dist node_modules", "rm -rf web/dist/*", "rm data/out/strata.duckdb",
    "rm -rf /private/tmp/strata-test",
    "source .env && databricks current-user me", "set -a; . .env; set +a",
    "uv run --env-file .env pytest -q", "uv run --env-file=.env pytest -q",
    "echo 'GENIE_SPACE_ID=abc' >> .env", "ls -la .env", "cat .env.example",
    "python3 .claude/hooks/guard.py --env-keys",
    "databricks bundle deploy -t dev", "databricks jobs run-now 123", "gh auth status", "gh api repos/owner/strata",
    "npm run build && npx playwright test", "python3 -c \"print('truncate the text')\"",
    "duckdb data/out/strata.duckdb \"DELETE FROM strata.ops.watermarks WHERE source = 'procnotices'\"",
    "echo 'DROP TABLE is blocked'", "curl -s 'https://search.worldbank.org/api/v3/wds?format=json'",
    "cp ../fairshare/src/db.py src/strata/db.py", "echo hi > /dev/null", "npm test 2>&1 | tail -5",
    "mkdir -p web/src/lib", "tee /private/tmp/strata.log", "sed -i '' 's/a/b/' web/src/App.tsx",
]

FILES_BLOCKED = [
    ("Read", {"file_path": f"{REPO}/.env"}),
    ("Read", {"file_path": f"{REPO}/.env.local"}),
    ("Write", {"file_path": f"{REPO}/.env", "content": "X=1"}),
    ("Grep", {"pattern": "TOKEN", "path": f"{REPO}/.env"}),
    ("Write", {"file_path": f"{REPO}/pipelines/bronze/reset.sql", "content": "DROP TABLE IF EXISTS strata.bronze.x;"}),
    ("Edit", {"file_path": f"{REPO}/src/strata/db.py", "old_string": "a",
              "new_string": 'cur.execute("DELETE FROM strata.ops.runs")'}),
    ("MultiEdit", {"file_path": f"{REPO}/src/strata/db.py",
                   "edits": [{"old_string": "a", "new_string": "TRUNCATE TABLE strata.silver.x"}]}),
    ("Write", {"file_path": os.path.join(os.path.dirname(REPO), "fairshare", "app.py"), "content": "x"}),
    ("Edit", {"file_path": os.path.expanduser("~/Desktop/notes.txt"), "old_string": "a", "new_string": "b"}),
]

FILES_ALLOWED = [
    ("Read", {"file_path": f"{REPO}/.env.example"}),
    ("Read", {"file_path": f"{REPO}/docs/PLAN.md"}),
    ("Write", {"file_path": f"{REPO}/src/strata/db.py",
               "content": 'cur.execute("DELETE FROM strata.ops.watermarks WHERE source = ?", (s,))'}),
    ("Write", {"file_path": f"{REPO}/pipelines/silver/contracts.sql",
               "content": "CREATE OR REPLACE TABLE strata.silver.contracts AS SELECT 1"}),
    ("Write", {"file_path": f"{REPO}/tests/test_sql_tool.py", "content": 'assert refuses("DROP TABLE strata.gold.x")'}),
    ("Write", {"file_path": f"{REPO}/docs/proposal.md", "content": "Prism never runs DROP TABLE."}),
    ("Write", {"file_path": os.path.expanduser("~/.claude/projects/strata/memory/note.md"), "content": "x"}),
    ("Read", {"file_path": os.path.join(os.path.dirname(REPO), "fairshare", "app.py")}),
]


class Commands(unittest.TestCase):
    def test_blocked(self):
        for command in BLOCKED:
            with self.subTest(command=command):
                self.assertEqual(bash(command), 2)

    def test_allowed(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertEqual(bash(command), 0)

    def test_files(self):
        for tool, data in FILES_BLOCKED:
            with self.subTest(tool=tool, data=data):
                self.assertEqual(run(tool, **data), 2)
        for tool, data in FILES_ALLOWED:
            with self.subTest(tool=tool, data=data):
                self.assertEqual(run(tool, **data), 0)


class Branches(unittest.TestCase):
    """History-changing commands depend on the branch the command runs on."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.unborn, self.main, self.ticket = (os.path.join(self.tmp.name, n) for n in ("unborn", "main", "ticket"))
        for path in (self.unborn, self.main, self.ticket):
            git(self.tmp.name, "init", "-q", "-b", "main", path)
        for path in (self.main, self.ticket):
            git(path, "commit", "-q", "--allow-empty", "-m", "first")
        git(self.ticket, "switch", "-q", "-c", "strata/01-scaffold")

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_commit_on_main_is_allowed(self):
        self.assertEqual(bash('git commit -m "Planning documents"', cwd=self.unborn), 0)

    def test_main_is_protected_after_its_first_commit(self):
        for command in ('git commit -m "x"', "git merge build/strata", "git reset HEAD~1",
                        "git revert -m 1 abc1234", "git cherry-pick abc1234", "git pull"):
            with self.subTest(command=command):
                self.assertEqual(bash(command, cwd=self.main), 2)
        self.assertEqual(bash(f'cd "{self.main}" && git commit -m x'), 2)
        self.assertEqual(bash(f'git -C "{self.main}" commit -m x'), 2)

    def test_main_allows_aborting_and_unstaging(self):
        for command in ("git merge --abort", "git reset", "git reset -- docs/STATUS.md"):
            with self.subTest(command=command):
                self.assertEqual(bash(command, cwd=self.main), 0)

    def test_ticket_branches_commit_and_merge_freely(self):
        for command in ('git commit -am "Add the scaffold"', "git merge build/strata", "git revert -m 1 abc1234",
                        "git rebase build/strata", 'git commit -m "Remove the -n flag from the docs"',
                        'git commit -m "Guard against DROP TABLE in the SQL tool"',
                        'uv run git commit -m "Guard against DROP TABLE in the SQL tool"'):
            with self.subTest(command=command):
                self.assertEqual(bash(command, cwd=self.ticket), 0)


class EnvKeys(unittest.TestCase):
    def test_lists_keys_without_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            git(tmp, "init", "-q", "-b", "main")
            with open(os.path.join(tmp, ".env.example"), "w") as f:
                f.write("A=\nB=\nC=\n")
            with open(os.path.join(tmp, ".env"), "w") as f:
                f.write("A='s3cret-value'\nB=\n")
            done = subprocess.run([sys.executable, HOOK, "--env-keys"], cwd=tmp, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0)
        self.assertIn("A: set", done.stdout)
        self.assertIn("B: empty", done.stdout)
        self.assertIn("C: missing", done.stdout)
        self.assertNotIn("s3cret", done.stdout)


if __name__ == "__main__":
    unittest.main()
