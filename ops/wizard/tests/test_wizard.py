"""The setup wizard, run whole in bash with fake databricks, az and browser commands.

The wizard is the interface a person uses, so these tests drive it the same way: answers on
standard input, then a look at what landed in the env file, the secret scope, the results
document and the screen. Expected keys come from .env.example, not from the wizard.
"""

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
WIZARD = REPO / "ops" / "wizard" / "strata-setup.sh"
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402

from strata.config import load_models  # noqa: E402

TOKEN = "dapi-good-token-1234"
AZURE_KEY = "azure-key-5678"
INSIGHTS = "InstrumentationKey=ik-91;IngestionEndpoint=https://eastus-8.in.example/;ApplicationId=app-0042"
CLIENT_ID = "sp-client-0001"
CLIENT_SECRET = "sp-secret-9999"
SECRETS = (TOKEN, AZURE_KEY, INSIGHTS, CLIENT_SECRET)

FAKE_DATABRICKS = r"""#!/bin/bash
echo "databricks $*" >> "$FAKE_LOG"
case "$1 $2" in
  "current-user me")
    if [[ "${DATABRICKS_AUTH_TYPE:-}" == "oauth-m2m" ]]; then
      [[ "${DATABRICKS_CLIENT_SECRET:-}" == "$FAKE_GOOD_SECRET" ]] || { echo "Error: invalid client secret" >&2; exit 1; }
    else
      [[ "${DATABRICKS_TOKEN:-}" == "$FAKE_GOOD_TOKEN" ]] || { echo "Error: invalid access token" >&2; exit 1; }
    fi
    if [[ -n "${FAKE_ME_NO_ID:-}" ]]; then echo '{"userName": "person@example.org"}'
    else echo '{"userName": "person@example.org", "id": "42"}'; fi ;;
  "warehouses list") echo '[{"id": "wh0123456789", "name": "Serverless Starter Warehouse"}]' ;;
  "secrets list-scopes")
    if [[ -f "$FAKE_STATE/scope" ]]; then echo '[{"name": "strata", "backend_type": "DATABRICKS"}]'; else echo '[]'; fi ;;
  "secrets create-scope") touch "$FAKE_STATE/scope" ;;
  "secrets put-secret") [[ -f "$FAKE_STATE/scope" ]] || exit 1; cat > "$FAKE_STATE/secret-$4" ;;
  "auth login") touch "$FAKE_STATE/oauth" ;;
  "auth token") [[ -f "$FAKE_STATE/oauth" ]] || exit 1; echo '{"access_token": "oauth-token"}' ;;
  "apps get")
    if [[ -f "$FAKE_STATE/app" ]]; then echo '{"name": "strata", "url": "https://strata-42.aws.databricksapps.com"}'
    else echo "Error: App with name strata does not exist or is deleted." >&2; exit 1; fi ;;
esac
"""

FAKE_AZ = r"""#!/bin/bash
echo "az $*" >> "$FAKE_LOG"
case "$1 $2" in
  "login "*) touch "$FAKE_STATE/az"; echo '[]' ;;
  "account show")
    [[ -f "$FAKE_STATE/az" ]] || { echo "Please run 'az login' to setup account." >&2; exit 1; }
    echo '{"id": "sub-0001", "name": "Azure subscription 1", "tenantId": "tenant-0001"}' ;;
  "account set") ;;
  "cognitiveservices account")
    case "$3 $4" in
      "keys list") echo "$FAKE_AZURE_KEY" ;;
      "deployment list") echo '[{"name": "gpt-5.4-mini", "sku": {"name": "GlobalStandard", "capacity": 100}},
        {"name": "gpt-5.4-nano", "sku": {"name": "GlobalBatch", "capacity": 2000}}]' ;;
    esac ;;
esac
"""

FAKE_BROWSER = """#!/bin/bash
echo "browser $*" >> "$FAKE_LOG"
"""

# env is a program of its own, so whatever it is given shows on its command line.
FAKE_ENV = """#!/bin/bash
echo "env $*" >> "$FAKE_LOG"
exec /usr/bin/env "$@"
"""


def example_keys():
    keys = []
    for line in (REPO / ".env.example").read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            keys.append(line.split("=", 1)[0])
    return keys


@pytest.fixture
def place(tmp_path):
    bin_dir, state = tmp_path / "bin", tmp_path / "state"
    bin_dir.mkdir()
    state.mkdir()
    for name, body in (("databricks", FAKE_DATABRICKS), ("az", FAKE_AZ), ("xdg-open", FAKE_BROWSER),
                       ("env", FAKE_ENV)):
        (bin_dir / name).write_text(body)
        (bin_dir / name).chmod(0o755)
    # The wizard's first run starts from the template, whatever results the committed document holds.
    dayone.ensure_document(tmp_path / "results.md", dayone.load_config())
    return tmp_path


def run_wizard(place, answers, **fakes):
    """Run the wizard with the fakes and these answers. Keyword arguments set or override the fakes' variables."""
    env = {
        "PATH": f"{place / 'bin'}:{os.environ['PATH']}",
        "HOME": str(place),
        "TERM": "dumb",
        "ENV_FILE": str(place / "wizard.env"),
        "STRATA_RESULTS": str(place / "results.md"),
        "FAKE_LOG": str(place / "calls.log"),
        "FAKE_STATE": str(place / "state"),
        "FAKE_GOOD_TOKEN": TOKEN,
        "FAKE_GOOD_SECRET": CLIENT_SECRET,
        "FAKE_AZURE_KEY": AZURE_KEY,
        **fakes,
    }
    return subprocess.run(["bash", str(WIZARD)], input="\n".join(answers) + "\n", env=env,
                          capture_output=True, text=True, timeout=120)


FIRST_RUN = [
    "",                                                      # Press Enter to start.
    "dbc-1234.cloud.databricks.com/?o=99",                   # 1. workspace address
    "y",                                                     #    the page let you make a token
    TOKEN,                                                   #    the token, hidden
    "",                                                      # 2. warehouse ID: Enter takes the one found
    "https://dbc-1234.cloud.databricks.com/genie/rooms/01f0abc?o=99",  # 3. Genie space
    "",                                                      # 4. Press Enter to open the sign-in page
    "",                                                      # 5. Press Enter to sign in to Azure
    "y",                                                     #    this is the subscription for Strata
    "",                                                      # 6. Press Enter when the project is open
    "",                                                      #    project endpoint: Enter takes the default
    "",                                                      #    Azure OpenAI endpoint: Enter takes the default
    "",                                                      # 7. Press Enter when all four are deployed
    "y",                                                     #    all four deployed
    "",                                                      # 8. Press Enter when the budget is saved
    "",                                                      # 9. Press Enter when the string is copied
    INSIGHTS,                                                #    connection string, hidden
    "",                                                      #    Press Enter when tracing is connected
    "",                                                      # 10. Press Enter when the evaluation is done
    "y",                                                     #    it finished with scores
    "https://ai.azure.com/evaluation/run-1",                 #    link to the evaluation
    "",                                                      # 11. Press Enter when you have tried
    "y",                                                     #    that person signed in
    "",                                                      # 12. Press Enter when the page is open
    "n",                                                     #    not upgraded yet
    "",                                                      #    who: Enter takes the default
    "2026-11-03",                                            #    the date
    "n",                                                     # 13. do not run the probes now
]

SECOND_RUN = [
    "",                    # start
    "",                    # 1. address kept; the saved token still works, so no token questions
    "",                    # 2. warehouse kept
    "",                    # 3. Genie space kept
                           # 4. already signed in: nothing to ask
    "y",                   # 5. already signed in to Azure: this is the subscription
    "", "", "",            # 6. project open, both endpoints kept
    "",                    # 7. deployed; test 8 passed already, so no question
    "",                    # 8. budget
    "", "", "",            # 9. string copied, connection string kept, tracing connected
                           # 10. test 9 passed already: nothing to ask
                           # 11. the person joined already and the app is still missing: nothing to ask
    "", "n", "", "2026-11-03",  # 12. page open, still not upgraded, who, date
    "n",                   # 13. no probes
]
STAGE_12_AT = 13  # where the second run's answers for stage 12 start


def env_values(path):
    return dayone.load_env(path)


def test_the_wizard_passes_a_shell_syntax_check():
    done = subprocess.run(["bash", "-n", str(WIZARD)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_a_first_run_fills_every_key_in_the_example_env_file(place):
    done = run_wizard(place, FIRST_RUN)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]

    values = env_values(place / "wizard.env")
    assert sorted(values) == sorted(example_keys())
    assert all(values.values()), [key for key, value in values.items() if not value]
    assert values["DATABRICKS_HOST"] == "https://dbc-1234.cloud.databricks.com"
    assert values["DATABRICKS_TOKEN"] == TOKEN
    assert values["DATABRICKS_WAREHOUSE_ID"] == "wh0123456789"
    assert values["GENIE_SPACE_ID"] == "01f0abc"
    assert values["FOUNDRY_TENANT_ID"] == "tenant-0001"
    assert values["AZURE_OPENAI_API_KEY"] == AZURE_KEY
    assert values["APPLICATIONINSIGHTS_CONNECTION_STRING"] == INSIGHTS
    assert stat.S_IMODE((place / "wizard.env").stat().st_mode) == 0o600


def test_a_first_run_over_a_copy_of_the_example_env_file_fills_every_key(place):
    shutil.copy(REPO / ".env.example", place / "wizard.env")
    done = run_wizard(place, FIRST_RUN)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    values = env_values(place / "wizard.env")
    assert all(values.values()), [key for key, value in values.items() if not value]
    assert values["AI_SEARCH_ENDPOINT"] == "strata-search"
    assert "Emptied" not in done.stdout


def test_the_app_secrets_land_in_the_secret_scope_and_the_token_does_not(place):
    run_wizard(place, FIRST_RUN)
    state = place / "state"
    assert (state / "secret-AZURE_OPENAI_API_KEY").read_text() == AZURE_KEY
    assert (state / "secret-APPLICATIONINSIGHTS_CONNECTION_STRING").read_text() == INSIGHTS
    assert sorted(p.name for p in state.glob("secret-*")) == [
        "secret-APPLICATIONINSIGHTS_CONNECTION_STRING", "secret-AZURE_OPENAI_API_KEY"]


def test_no_secret_reaches_the_screen_or_a_command_line(place):
    done = run_wizard(place, FIRST_RUN)
    shown = done.stdout + done.stderr + (place / "calls.log").read_text() + (place / "results.md").read_text()
    for secret in SECRETS:
        assert secret not in shown


# 1. no token could be made, so try a service principal: its client ID, then its secret, hidden
SERVICE_PRINCIPAL_RUN = FIRST_RUN[:2] + ["n", "y", CLIENT_ID, CLIENT_SECRET] + FIRST_RUN[4:]


def test_a_service_principal_keeps_the_default_path_and_its_secret_off_every_command_line(place):
    done = run_wizard(place, SERVICE_PRINCIPAL_RUN)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    values = env_values(place / "wizard.env")
    assert values["DATABRICKS_CLIENT_ID"] == CLIENT_ID and values["DATABRICKS_CLIENT_SECRET"] == CLIENT_SECRET
    assert "DATABRICKS_TOKEN" not in values
    results = dayone.read_results(place / "results.md")
    assert results["test-7"]["Status"] == "passed"
    assert dayone.path_kind(7, place / "results.md") == "default"
    shown = done.stdout + done.stderr + (place / "calls.log").read_text() + (place / "results.md").read_text()
    assert CLIENT_SECRET not in shown


def test_the_service_principal_step_says_the_app_s_secret_lives_until_the_next_restart_and_when_the_fallback_covers_it(
        place):
    """Ticket 129: the platform makes the App's service principal a new secret each time it starts the App again, so
    the wizard says how long that secret lives and what covers it. This path saves no personal access token, so the
    fallback does not cover the person who reads it, and the wizard says that too."""
    done = run_wizard(place, SERVICE_PRINCIPAL_RUN)
    shown = " ".join(line.strip() for line in done.stdout.splitlines())

    assert ("A secret of the App's own service principal lives only until the platform next restarts the App, "
            "because the platform then makes it a new one.") in shown
    assert ("When the workspace refuses it, the scripts that write as the App, such as the seed command, write with "
            "a personal access token in DATABRICKS_TOKEN instead.") in shown
    assert "This path saves no token, so on it the seed command needs the App's new secret after each restart." in shown
    assert "You never need to paste the App's secret" not in shown


def test_the_wizard_records_tests_six_seven_eight_nine_and_the_pay_as_you_go_step(place):
    run_wizard(place, FIRST_RUN)
    results = dayone.read_results(place / "results.md")
    assert results["test-7"]["Status"] == "passed"
    assert results["test-8"]["Status"] == "passed"
    assert results["test-9"]["Status"] == "passed"
    assert any("https://ai.azure.com/evaluation/run-1" in line for line in results["test-9"]["Evidence"])
    assert results["test-6"]["Status"] == "waiting"
    assert results["test-6"]["Chosen path"].startswith("Default")
    assert results["payg"]["Status"] == "Planned for November 3, 2026."
    assert results["payg"]["Who"] == "The subscription owner (the user)"
    assert "person@example.org" not in (place / "results.md").read_text()


def test_the_wizards_evidence_for_tests_seven_and_eight_is_command_output(place):
    done = run_wizard(place, FIRST_RUN)
    results = dayone.read_results(place / "results.md")
    assert "databricks current-user me returned the user ID 42." in results["test-7"]["Evidence"][0]
    assert results["test-8"]["Evidence"][0] == (
        "az cognitiveservices account deployment list returned gpt-5.4-mini (GlobalStandard), "
        "gpt-5.4-nano (GlobalBatch).")
    assert "gpt-5.4-nano  GlobalBatch  2000" in done.stdout



def test_test_sevens_evidence_says_so_when_the_user_id_cannot_be_read(place):
    run_wizard(place, FIRST_RUN, FAKE_ME_NO_ID="1")
    evidence = dayone.read_results(place / "results.md")["test-7"]["Evidence"][0]
    assert evidence.startswith(
        "databricks current-user me accepted the credentials, but I could not read the user ID in its answer.")
    assert "returned the user ID" not in evidence


def test_stage_seven_names_each_deployment_from_the_model_file_and_says_azure_counts_in_thousands(place):
    done = run_wizard(place, FIRST_RUN)
    models = load_models()
    assert f"Deploy {models['batch'].deployment} as Global Batch, named {models['batch'].deployment}." in done.stdout
    assert (f"Strata asks {models['embed'].deployment} for {models['embed'].dimensions:,} dimensions in each request"
            in done.stdout)
    assert "Azure shows capacity in thousands of tokens." in done.stdout
    assert "100 on a Global Standard deployment means 100,000 tokens per minute." in done.stdout


def test_a_service_principal_that_replaces_a_dead_token_clears_the_token(place):
    run_wizard(place, FIRST_RUN)
    assert env_values(place / "wizard.env")["DATABRICKS_TOKEN"] == TOKEN
    # The saved token stops working. The page lets no token be made, so the person tries a service principal.
    answers = SECOND_RUN[:2] + ["n", "y", CLIENT_ID, CLIENT_SECRET] + SECOND_RUN[2:]
    done = run_wizard(place, answers, FAKE_GOOD_TOKEN="dapi-a-newer-token")
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    values = env_values(place / "wizard.env")
    assert values["DATABRICKS_CLIENT_SECRET"] == CLIENT_SECRET
    assert not values.get("DATABRICKS_TOKEN")
    assert TOKEN not in (place / "wizard.env").read_text()
    assert f"Emptied DATABRICKS_TOKEN in {place / 'wizard.env'}." in done.stdout
    assert "Saved DATABRICKS_TOKEN" not in done.stdout
    assert "The saved token no longer works, so the service principal replaces it." in done.stdout


def test_a_second_run_with_enter_keeps_the_same_env_file(place):
    run_wizard(place, FIRST_RUN)
    first = (place / "wizard.env").read_text()
    done = run_wizard(place, SECOND_RUN)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    assert (place / "wizard.env").read_text() == first
    assert (place / "state" / "secret-AZURE_OPENAI_API_KEY").read_text() == AZURE_KEY


def test_a_second_run_keeps_a_saved_value_with_a_single_quote_as_it_is(place):
    run_wizard(place, FIRST_RUN)
    path = place / "wizard.env"
    seeded = re.sub(r"^GENIE_SPACE_ID=.*$", "GENIE_SPACE_ID='it'\\''s'", path.read_text(), flags=re.M)
    path.write_text(seeded)
    done = run_wizard(place, SECOND_RUN)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    assert path.read_text() == seeded
    assert env_values(path)["GENIE_SPACE_ID"] == "it's"


def test_a_second_run_after_the_app_is_deployed_finishes_test_six(place):
    # The second run asks stage 10's questions only when the first run left test 9 unrecorded, so a first run
    # that failed says so here, not as the second run's end of input at stage 10 (ticket 56).
    first = run_wizard(place, FIRST_RUN)
    assert first.returncode == 0, first.stdout[-3000:] + first.stderr[-3000:]
    assert dayone.read_results(place / "results.md")["test-9"]["Status"] == "passed"
    (place / "state" / "app").touch()
    answers = SECOND_RUN[:STAGE_12_AT] + ["y"] + SECOND_RUN[STAGE_12_AT:]   # 11. the app opened
    done = run_wizard(place, answers)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    results = dayone.read_results(place / "results.md")
    assert results["test-6"]["Status"] == "passed"
    assert "https://strata-42.aws.databricksapps.com" in done.stdout


def test_a_second_run_after_the_upgrade_skips_the_pay_as_you_go_stage(place):
    upgraded = FIRST_RUN[:-4] + ["y", "n"]           # 12. upgraded just now; 13. no probes
    assert FIRST_RUN[-4:] == ["n", "", "2026-11-03", "n"]
    run_wizard(place, upgraded)
    assert dayone.read_results(place / "results.md")["payg"]["Status"].startswith("Done on ")
    done = run_wizard(place, SECOND_RUN[:STAGE_12_AT] + ["n"])
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    assert "already moved to pay-as-you-go" in done.stdout


def test_a_badly_typed_date_in_stage_twelve_shows_one_sentence_and_asks_again(place):
    assert FIRST_RUN[-2:] == ["2026-11-03", "n"]
    done = run_wizard(place, FIRST_RUN[:-2] + ["11/03/2026", "2026-11-03", "n"])
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    assert "11/03/2026 is not a date in the form YYYY-MM-DD." in done.stderr
    assert "usage:" not in done.stdout + done.stderr
    assert dayone.read_results(place / "results.md")["payg"]["Status"] == "Planned for November 3, 2026."


def test_a_token_databricks_refuses_is_not_saved(place):
    answers = FIRST_RUN[:3] + ["dapi-wrong", "n", "n", "wh-typed"] + FIRST_RUN[5:]
    done = run_wizard(place, answers)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    values = env_values(place / "wizard.env")
    assert "DATABRICKS_TOKEN" not in values
    assert dayone.read_results(place / "results.md")["test-7"]["Status"] == "failed"


# ── The static trace: the table in the wizard's header against its stages ──

def destination_table():
    rows = {}
    for line in WIZARD.read_text().splitlines():
        found = re.match(r"^#   ([A-Z][A-Z0-9_]+)\s{2,}(.+?)\s{2,}(\S.*)$", line)
        if found:
            rows[found[1]] = (found[2], found[3])
    return rows


def calls(name):
    return set(re.findall(rf"^\s*{name} ([A-Z][A-Z0-9_]+)\b", WIZARD.read_text(), re.M))


def test_the_destination_table_covers_every_key_in_the_example_env_file():
    table = destination_table()
    for key in example_keys():
        assert key in table, f"{key} is missing from the wizard's table"
        assert ".env" in table[key][0]


def test_every_value_lands_where_the_table_says_and_nowhere_else():
    table = destination_table()
    written, scoped = calls("write_env"), calls("put_scope_secret")
    hidden = calls("ask_secret") | calls("ask_secret_required")
    typed = calls("ask") | calls("ask_required") | calls("ask_with_default")
    for key, (destination, entry) in table.items():
        assert (key in written) == (".env" in destination), key
        assert (key in scoped) == ("secret scope" in destination), key
        if "hidden" in entry:
            assert key in hidden and key not in typed, key
        if "typed" in entry:
            assert key in typed and key not in hidden, key
    assert written | scoped | hidden | typed <= set(table), (written | scoped | hidden | typed) - set(table)
