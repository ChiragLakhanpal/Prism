#!/usr/bin/env bash
#
# Strata setup wizard: credentials, Azure caps and the day-one tests (ticket 03).
#
# Run it in your own terminal, from the main checkout:
#
#     bash ops/wizard/strata-setup.sh
#
# Only you can sign in to the Databricks workspace, the Azure portal and Microsoft Foundry,
# so this wizard tells you what to click and saves what you copy back. It saves values in the
# main checkout's .env, which git ignores, and the app's secrets in the Databricks secret scope
# named in ops/dayone/dayone.toml. It writes test results to docs/day-one-results.md in the
# same checkout as this script, and that file holds no secrets. It is safe to run again:
# Enter keeps each saved value, and stages whose test already passed have nothing to ask.
#
# Where each value goes. ops/wizard/tests/test_wizard.py checks this table against the stages.
#   Key                                    Goes to                          Entered as
#   DATABRICKS_HOST                        .env                             typed
#   DATABRICKS_TOKEN                       .env                             hidden
#   DATABRICKS_CLIENT_ID                   .env, only without a token       typed
#   DATABRICKS_CLIENT_SECRET               .env, only without a token       hidden
#   DATABRICKS_WAREHOUSE_ID                .env                             typed, or found by the CLI
#   GENIE_SPACE_ID                         .env                             typed
#   AI_SEARCH_ENDPOINT                     .env                             default from dayone.toml
#   FOUNDRY_TENANT_ID                      .env                             read from az, or typed
#   FOUNDRY_PROJECT_ENDPOINT               .env                             typed
#   AZURE_OPENAI_ENDPOINT                  .env                             typed
#   AZURE_OPENAI_API_KEY                   .env and secret scope            hidden, or read from az
#   APPLICATIONINSIGHTS_CONNECTION_STRING  .env and secret scope            hidden
#   AZURE_SUBSCRIPTION                     nowhere, only az account set     typed
#   DEPLOY_PROBLEM                         results document                 typed
#   EVALUATION_LINK                        results document                 typed
#   EVALUATION_PROBLEM                     results document                 typed
#   PAYG_WHO                               results document                 typed
#   PAYG_DUE                               results document                 typed
#
# The library below follows the wizard skill's template (mattpocock-skills:wizard). Its
# messages are reworded to follow docs/agents/unslop.md, its GitHub helpers are gone because
# the GitHub repo stays out of this wizard, and finish() also lists the secret scope.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Wizard library: the same steps and prompts in every wizard.
# ──────────────────────────────────────────────────────────────────────────

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  BOLD=$(tput bold); DIM=$(tput dim); RESET=$(tput sgr0)
  BLUE=$(tput setaf 4); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3)
else
  BOLD=""; DIM=""; RESET=""; BLUE=""; GREEN=""; YELLOW=""
fi

# Author sets this at the top of the stages section.
TOTAL_STAGES=0

_STAGE_INDEX=0
ENV_FILE="${ENV_FILE:-.env}"
WRITTEN_ENV=()    # KEYs written to ENV_FILE this run
WRITTEN_SCOPE=()  # KEYs saved in the Databricks secret scope this run
SKIPPED=()        # steps the wizard could not take, for the person to take later

# _clear wipes the terminal so only the current step is on screen. It does nothing when
# output is not a terminal, so piped logs stay readable.
_clear() {
  [[ -t 1 ]] || return 0
  if command -v tput >/dev/null 2>&1 && tput clear 2>/dev/null; then return 0; fi
  printf '\033[2J\033[3J\033[H'
}

# banner "Title" shows the opening frame: what this wizard does.
banner() {
  _clear
  printf '\n%s%s  %s%s\n' "$BOLD" "$BLUE" "$1" "$RESET"
  printf '%s  This wizard has %s stages.%s\n\n' "$DIM" "$TOTAL_STAGES" "$RESET"
  printf '%s  You work in the browser. The wizard tells you what to click and saves the values\n' "$DIM"
  printf '  you copy back. You can stop at any time with Ctrl-C and run it again later.\n'
  printf '  It remembers the values it already saved.%s\n\n' "$RESET"
  pause "Press Enter to start."
}

# stage "Name" clears the screen, then names the stage and shows how far along you are.
stage() {
  _clear
  _STAGE_INDEX=$((_STAGE_INDEX + 1))
  printf '\n%s%sStage %s of %s: %s%s\n\n' \
    "$BOLD" "$BLUE" "$_STAGE_INDEX" "$TOTAL_STAGES" "$1" "$RESET"
}

# say "..." prints a plain instruction line.
say()  { printf '  %s\n' "$1"; }
# step "..." is an action the person takes in the browser.
step() { printf '  %s-%s %s\n' "$BLUE" "$RESET" "$1"; }
note() { printf '  %s%s%s\n' "$DIM" "$1" "$RESET"; }
warn() { printf '  %s%s%s\n' "$YELLOW" "$1" "$RESET"; }

# open_url URL opens it in the person's browser, on macOS, Linux and WSL.
open_url() {
  local url="$1"
  printf '  %sOpening %s in your browser.%s\n' "$GREEN" "$url" "$RESET"
  { if   command -v wslview     >/dev/null 2>&1; then wslview "$url"
    elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$url"
    elif command -v xdg-open    >/dev/null 2>&1; then xdg-open "$url"
    elif command -v open        >/dev/null 2>&1; then open "$url"
    else false; fi
  } >/dev/null 2>&1 || warn "I could not open a browser. Please open this address yourself: $url"
}

# pause "msg" waits for the person to finish the manual part.
pause() {
  printf '  %s%s%s ' "$DIM" "${1:-Press Enter to continue.}" "$RESET"
  read -r _ || true
}

# confirm "question" is a yes or no gate; it succeeds on yes. Enter means no.
confirm() {
  local reply=""
  printf '  %s%s [y/N]%s ' "$YELLOW" "$1" "$RESET"
  read -r reply || true
  [[ "$reply" =~ ^[Yy] ]]
}

# _existing KEY prints KEY's current value in ENV_FILE, if any, with write_env's single
# quotes or a plain dotenv double-quoted value undone.
_existing() {
  [[ -f "$ENV_FILE" ]] || return 1
  local line value sq="'\\''" q="'"; line=$(grep -E "^${1}=" "$ENV_FILE" | tail -n1) || return 1
  value="${line#*=}"
  if [[ "$value" == \'*\' ]]; then value="${value:1:${#value}-2}"; value="${value//"$sq"/$q}"
  elif [[ "$value" == \"*\" ]]; then
    value="${value:1:${#value}-2}"
    [[ "$value" == *[\\\$\"]* ]] && return 1   # escapes, $ or ": cannot decode safely, so ask again
  fi
  printf '%s' "$value"
}

# ask KEY "Prompt" reads a value into $KEY. On a second run it offers the saved .env value,
# and Enter keeps it. The person sees what they type. It fails at the end of input.
ask() {
  local key="$1" prompt="$2" current input s=$'\001' e=$'\002' p rc=0
  current=$(_existing "$key" || true)
  # Readline needs the colour codes wrapped in \001..\002 to place the cursor.
  p="  $s$BOLD$e$prompt$s$RESET$e "
  [[ -n "$current" ]] && p+="$s$DIM$e(Press Enter to keep the saved value.)$s$RESET$e "
  read -e -r -p "$p" input || rc=1
  if (( rc )) && [[ -z "$input" ]]; then return 1; fi
  [[ -z "$input" && -n "$current" ]] && input="$current"
  printf -v "$key" '%s' "$input"
}

# ask_secret KEY "Prompt" is like ask, but the input stays hidden.
ask_secret() {
  local key="$1" prompt="$2" current input rc=0
  current=$(_existing "$key" || true)
  if [[ -n "$current" ]]; then
    printf '  %s%s%s %s(Press Enter to keep the saved value.)%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -rs input || rc=1
  printf '\n'
  if (( rc )) && [[ -z "$input" ]]; then return 1; fi
  [[ -z "$input" && -n "$current" ]] && input="$current"
  printf -v "$key" '%s' "$input"
}

# write_env KEY VALUE replaces KEY's line in ENV_FILE where it stands, or adds it at the end,
# and sets $KEY. Running it twice gives the same file, in the same order. It creates
# ENV_FILE readable only by you, writes through a symlink, and keeps an existing file's mode.
# Its working copy sits beside ENV_FILE, where git ignores it, and goes away even after Ctrl-C.
write_env() {
  local key="$1" value="$2" tmp sq="'\\''" entry line replaced=0
  [[ -e "$ENV_FILE" ]] || (umask 077 && : > "$ENV_FILE")
  entry=$(printf "%s='%s'" "$key" "${value//\'/$sq}")
  tmp=$(mktemp "${ENV_FILE}.XXXXXX")
  trap 'rm -f "$tmp"' EXIT
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "$key="* ]]; then
      (( replaced )) || printf '%s\n' "$entry" >> "$tmp"
      replaced=1
    else
      printf '%s\n' "$line" >> "$tmp"
    fi
  done < "$ENV_FILE"
  (( replaced )) || printf '%s\n' "$entry" >> "$tmp"
  cat "$tmp" > "$ENV_FILE"
  rm -f "$tmp"
  trap - EXIT
  printf -v "$key" '%s' "$value"
  if [[ -z "$value" ]]; then
    printf '  %sEmptied %s in %s.%s\n' "$GREEN" "$key" "$ENV_FILE" "$RESET"
    return
  fi
  WRITTEN_ENV+=("$key")
  printf '  %sSaved %s in %s.%s\n' "$GREEN" "$key" "$ENV_FILE" "$RESET"
}

# finish clears the screen, then lists everything the wizard saved and what is left to do.
finish() {
  _clear
  printf '\n%s%s  The wizard is done.%s\n' "$BOLD" "$GREEN" "$RESET"
  (( ${#WRITTEN_ENV[@]} ))   && note "It saved ${#WRITTEN_ENV[@]} values in $ENV_FILE: ${WRITTEN_ENV[*]}."
  (( ${#WRITTEN_SCOPE[@]} )) && note "It saved ${#WRITTEN_SCOPE[@]} secrets in the secret scope $SCOPE: ${WRITTEN_SCOPE[*]}."
  if (( ${#SKIPPED[@]} )); then
    printf '\n'; warn "These steps are still yours to take:"
    for s in "${SKIPPED[@]}"; do note "  - $s"; done
  fi
  printf '\n'
}

# ──────────────────────────────────────────────────────────────────────────
# STAGES: one stage() per step the person takes. Keep every stage inside run_wizard and the
# last line as it is: bash then reads the whole file before the first prompt, so an edit
# made while the wizard runs cannot break it.
# ──────────────────────────────────────────────────────────────────────────

# Places. The wizard writes .env in the main checkout, also when it runs from a worktree,
# because secrets live only there (CLAUDE.md rule 7). It writes the results document beside
# this script, so the results travel with the branch. ENV_FILE and STRATA_RESULTS point it
# elsewhere for tests.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MAIN="$ROOT"
if common=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null); then
  MAIN="$(dirname "$common")"
fi
[[ "$ENV_FILE" == ".env" ]] && ENV_FILE="$MAIN/.env"
RESULTS="${STRATA_RESULTS:-$ROOT/docs/day-one-results.md}"
PYTHON=""
DBX_OK=0         # 1 once a token or a service principal reaches Databricks
SCOPE_READY=0    # 1 once the secret scope exists

# find_python picks a Python that has tomllib (3.11 or later) for ops/dayone/dayone.py.
find_python() {
  local candidate
  for candidate in python3.12 python3.13 python3.14 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import tomllib' >/dev/null 2>&1; then
      PYTHON=$(command -v "$candidate")
      return 0
    fi
  done
  return 1
}

# dayone runs ops/dayone/dayone.py on this run's results document.
dayone() { "$PYTHON" "$ROOT/ops/dayone/dayone.py" --results "$RESULTS" "$@"; }

# setting NAME prints one value from ops/dayone/dayone.toml.
setting() { dayone get "$1"; }

# model_value ROLE [FIELD] prints one role's deployment, or its dimensions, from config/models.toml,
# the one place that names a model (spec, "Ten single places").
model_value() { dayone model "$@"; }

# example_value KEY prints KEY's value in .env.example.
example_value() { grep -E "^$1=" "$ROOT/.env.example" | head -n1 | cut -d= -f2-; }

# with_commas 100000 prints 100,000.
with_commas() { "$PYTHON" -c 'import sys; print(f"{int(sys.argv[1]):,}")' "$1"; }

# json_get EXPR reads JSON on standard input and prints EXPR, where d is the parsed value.
json_get() {
  "$PYTHON" -c 'import json, sys
d = json.load(sys.stdin)
print(eval(sys.argv[1]))' "$1" 2>/dev/null
}

# ask_required KEY "Prompt" asks until the person gives a value.
ask_required() {
  while true; do
    ask "$1" "$2" || return 1
    if [[ -n "${!1}" ]]; then return 0; fi
    warn "Strata needs this value. Please paste it."
  done
}

# ask_secret_required KEY "Prompt" asks, hidden, until the person gives a value.
ask_secret_required() {
  while true; do
    ask_secret "$1" "$2" || return 1
    if [[ -n "${!1}" ]]; then return 0; fi
    warn "Strata needs this value. Please paste it."
  done
}

# ask_with_default KEY "Prompt" DEFAULT is like ask_required, but Enter takes DEFAULT when
# .env has no value for KEY yet.
ask_with_default() {
  local key="$1" prompt="$2" default="$3"
  if [[ -n "$(_existing "$key" || true)" || -z "$default" ]]; then
    ask_required "$key" "$prompt"
    return
  fi
  ask "$key" "$prompt (Press Enter for $default.)" || return 1
  if [[ -z "${!key}" ]]; then printf -v "$key" '%s' "$default"; fi
  return 0
}

# record_test N STATUS RESULT [EVIDENCE ...] writes one test's result in the results document.
record_test() {
  local number="$1" status="$2" result="$3"
  shift 3
  record_test_with_path "$number" "$status" "" "$result" ${@+"$@"}
}

# record_test_with_path N STATUS PATH RESULT [EVIDENCE ...] also names the chosen path.
record_test_with_path() {
  local number="$1" status="$2" path="$3" result="$4" item
  shift 4
  local args=(--test "$number" --status "$status" --result "$result")
  [[ -n "$path" ]] && args+=(--path "$path")
  for item in ${@+"$@"}; do args+=(--evidence "$item"); done
  if dayone record "${args[@]}" >/dev/null; then
    note "I wrote the result of test $number in $RESULTS."
  else
    SKIPPED+=("Record the result of test $number in $RESULTS, because the wizard could not write it.")
    warn "I could not write the result of test $number in $RESULTS."
  fi
}

# test_status N prints the status the results document holds for test N.
test_status() { dayone field "test-$1" Status 2>/dev/null || true; }

# dbx runs the Databricks command line with the token or service principal from this run,
# never with a profile from your own configuration. The subshell exports the values, so they
# reach databricks only through its environment and never appear on a command line.
dbx() {
  (
    unset DATABRICKS_CONFIG_PROFILE
    export DATABRICKS_HOST
    if [[ -n "${DATABRICKS_TOKEN:-}" ]]; then
      export DATABRICKS_TOKEN DATABRICKS_AUTH_TYPE=pat
    else
      export DATABRICKS_CLIENT_ID DATABRICKS_CLIENT_SECRET DATABRICKS_AUTH_TYPE=oauth-m2m
    fi
    exec databricks "$@"
  )
}

databricks_works() { dbx current-user me -o json >/dev/null 2>&1; }

# user_id_evidence prints test 7's evidence: the user ID Databricks returns for these credentials.
user_id_evidence() {
  local id
  id=$(dbx current-user me -o json 2>/dev/null | json_get 'd["id"]' || true)
  if [[ -n "$id" ]]; then
    printf 'databricks current-user me returned the user ID %s.' "$id"
  else
    printf 'databricks current-user me accepted the credentials, but I could not read the user ID in its answer.'
  fi
}

# put_scope_secret KEY VALUE saves VALUE as KEY in the app's secret scope. The value goes in
# on standard input, so it never appears on a command line.
put_scope_secret() {
  local key="$1" value="$2"
  if (( ! DBX_OK )); then
    SKIPPED+=("Save $key in the secret scope $SCOPE once Databricks accepts a token: databricks secrets put-secret $SCOPE $key")
    warn "I could not save $key in the secret scope, because Databricks has not accepted a token."
    return 0
  fi
  if (( ! SCOPE_READY )); then
    if ! dbx secrets list-scopes -o json 2>/dev/null \
        | "$PYTHON" -c 'import json, sys; sys.exit(0 if any(s.get("name") == sys.argv[1] for s in json.load(sys.stdin) or []) else 1)' "$SCOPE"; then
      if ! dbx secrets create-scope "$SCOPE" >/dev/null 2>&1; then
        SKIPPED+=("Make the secret scope $SCOPE: databricks secrets create-scope $SCOPE")
        warn "I could not make the secret scope $SCOPE, so $key is only in $ENV_FILE."
        return 0
      fi
      note "I made the secret scope $SCOPE."
    fi
    SCOPE_READY=1
  fi
  if printf '%s' "$value" | dbx secrets put-secret "$SCOPE" "$key" >/dev/null 2>&1; then
    WRITTEN_SCOPE+=("$key")
    printf '  %sSaved %s in the secret scope %s.%s\n' "$GREEN" "$key" "$SCOPE" "$RESET"
  else
    SKIPPED+=("Save $key in the secret scope $SCOPE: databricks secrets put-secret $SCOPE $key")
    warn "I could not save $key in the secret scope $SCOPE."
  fi
}

# workspace_address turns whatever was pasted into https://<host>.
workspace_address() {
  local address="$1"
  address="${address#http://}"
  address="${address#https://}"
  address="${address%%/*}"
  address="${address%%\?*}"
  printf 'https://%s' "$address"
}

# genie_space_id takes a Genie space address or ID and prints the ID.
genie_space_id() {
  local id="$1"
  id="${id##*/rooms/}"
  id="${id%%[/?#]*}"
  printf '%s' "$id"
}

# openai_endpoint makes sure the Azure OpenAI endpoint ends in /openai/v1.
openai_endpoint() {
  local endpoint="${1%/}"
  [[ "$endpoint" == */openai/v1 ]] || endpoint="$endpoint/openai/v1"
  printf '%s' "$endpoint"
}

preflight() {
  local missing=() tool
  for tool in databricks az git; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
  done
  find_python || missing+=("python3, version 3.11 or later")
  if (( ${#missing[@]} )); then
    printf '\n'
    warn "The wizard needs these commands, and this computer does not have them yet:"
    for tool in "${missing[@]}"; do note "  - $tool"; done
    warn "Install them, then run the wizard again."
    exit 1
  fi
  if [[ "$ENV_FILE" == "$MAIN"/* ]] && ! git -C "$MAIN" check-ignore -q "$ENV_FILE"; then
    warn "git does not ignore $ENV_FILE, so secrets saved there could reach git. I stopped before saving anything."
    exit 1
  fi
}

# ── Stage helpers that hold a whole branch of a stage ────────────────────

make_token() {
  open_url "$DATABRICKS_HOST"
  step "Click your user icon at the top right, then click Settings."
  step "Under User, click Developer. Next to Access tokens, click Manage."
  step "Click Generate new token. Name it strata, let it last 90 days, and click Generate."
  step "Copy the token. Databricks shows it only once."
  if confirm "Did the page let you make a token?"; then
    while true; do
      ask_secret_required DATABRICKS_TOKEN "Paste the token. It stays hidden while you paste:"
      if databricks_works; then
        write_env DATABRICKS_TOKEN "$DATABRICKS_TOKEN"
        DBX_OK=1
        record_test 7 passed "A personal access token works." \
          "$(user_id_evidence) It used a new personal access token."
        return 0
      fi
      warn "Databricks did not accept that token."
      confirm "Do you want to paste a different token?" || break
    done
    DATABRICKS_TOKEN=""
  fi
  if confirm "Do you want to try a service principal instead?"; then
    service_principal
  else
    record_test 7 failed "I could not make a personal access token that Databricks accepts." \
      "The person could not make a working token, and did not try a service principal."
  fi
}

service_principal() {
  DATABRICKS_TOKEN=""
  open_url "$DATABRICKS_HOST"
  step "Click your user icon, then Settings. Under Workspace admin, open Identity and access."
  step "Next to Service principals, click Manage. Click Add service principal, then Add new."
  step "Name it strata-probes and click Add. Open it, open the Secrets tab, and click Generate secret."
  step "Copy the client ID and the secret. Databricks shows the secret only once."
  ask_required DATABRICKS_CLIENT_ID "Paste the client ID:"
  ask_secret_required DATABRICKS_CLIENT_SECRET "Paste the secret. It stays hidden while you paste:"
  if databricks_works; then
    write_env DATABRICKS_CLIENT_ID "$DATABRICKS_CLIENT_ID"
    write_env DATABRICKS_CLIENT_SECRET "$DATABRICKS_CLIENT_SECRET"
    # A saved token that stopped working would still come first for dbx and the probes, so empty it.
    if [[ -n "$(_existing DATABRICKS_TOKEN || true)" ]]; then
      write_env DATABRICKS_TOKEN ""
      note "The saved token no longer works, so the service principal replaces it."
    fi
    DBX_OK=1
    record_test_with_path 7 passed \
      "Default, with the service principal strata-probes. Scripts and probes reach Databricks with it, because a personal access token could not be made." \
      "A service principal works, and a personal access token did not." \
      "$(user_id_evidence) It used the client ID and secret of the service principal strata-probes."
  else
    record_test 7 failed "Neither a personal access token nor a service principal reached Databricks." \
      "Databricks refused the token and the service principal's client ID and secret."
  fi
}

run_wizard() {

TOTAL_STAGES=13

unset DATABRICKS_HOST DATABRICKS_TOKEN DATABRICKS_CLIENT_ID DATABRICKS_CLIENT_SECRET DATABRICKS_CONFIG_PROFILE \
  DATABRICKS_AUTH_TYPE DATABRICKS_WAREHOUSE_ID GENIE_SPACE_ID AZURE_OPENAI_API_KEY \
  APPLICATIONINSIGHTS_CONNECTION_STRING 2>/dev/null || true

preflight
SCOPE=$(setting names.secret_scope)
PROFILE=$(setting names.oauth_profile)
APP=$(setting names.app)
RESOURCE_GROUP=$(setting names.resource_group)
FOUNDRY_RESOURCE=$(setting names.foundry_resource)
DEADLINE=$(setting payg.deadline)
DEADLINE_LONG=$("$PYTHON" -c 'import datetime, sys; d = datetime.date.fromisoformat(sys.argv[1]); print(f"{d:%B} {d.day}, {d.year}")' "$DEADLINE")
dayone init >/dev/null

banner "Strata setup: credentials, Azure caps and the day-one tests"

# ── Stage 1 ───────────────────────────────────────────────────────────────
stage "Your Databricks workspace and a personal access token (test 7)"
say "Strata reaches your Databricks workspace with a personal access token. This stage also"
say "answers day-one test 7, which asks whether you can make a token or a service principal."
say ""
ask_required DATABRICKS_HOST "Paste your workspace address, such as https://dbc-1234abcd-5678.cloud.databricks.com:"
write_env DATABRICKS_HOST "$(workspace_address "$DATABRICKS_HOST")"

DATABRICKS_TOKEN=$(_existing DATABRICKS_TOKEN || true)
DATABRICKS_CLIENT_ID=$(_existing DATABRICKS_CLIENT_ID || true)
DATABRICKS_CLIENT_SECRET=$(_existing DATABRICKS_CLIENT_SECRET || true)
if [[ -n "$DATABRICKS_TOKEN$DATABRICKS_CLIENT_SECRET" ]] && databricks_works; then
  DBX_OK=1
  say "The saved credentials still work, so you do not need new ones."
  if [[ "$(test_status 7)" != "passed" ]]; then
    record_test 7 passed "The saved Databricks credentials work." "$(user_id_evidence) It used the saved credentials."
  fi
else
  DATABRICKS_TOKEN=""
  make_token
fi

# ── Stage 2 ───────────────────────────────────────────────────────────────
stage "The Databricks SQL warehouse"
say "Strata's queries run on the workspace's SQL warehouse. Free Edition has one."
found=""
if (( DBX_OK )); then
  found=$(dbx warehouses list -o json 2>/dev/null \
    | json_get '(d[0]["id"] + "|" + d[0].get("name", "")) if len(d or []) == 1 else ""' || true)
fi
if [[ -n "$found" ]]; then
  say "I found one warehouse, \"${found#*|}\", with the ID ${found%%|*}."
  ask_with_default DATABRICKS_WAREHOUSE_ID "Press Enter to use it, or paste another warehouse ID." "${found%%|*}"
else
  open_url "$DATABRICKS_HOST/sql/warehouses"
  step "Click the warehouse's name. Its ID is the last part of the address in your browser, after /sql/warehouses/."
  ask_required DATABRICKS_WAREHOUSE_ID "Paste the warehouse ID:"
fi
write_env DATABRICKS_WAREHOUSE_ID "$DATABRICKS_WAREHOUSE_ID"

# An empty saved value counts as none, so a copy of .env.example still gets the default.
AI_SEARCH_ENDPOINT=$(_existing AI_SEARCH_ENDPOINT || true)
[[ -n "$AI_SEARCH_ENDPOINT" ]] || AI_SEARCH_ENDPOINT=$(setting names.ai_search_endpoint)
say "Strata's AI Search endpoint will be named $AI_SEARCH_ENDPOINT."
write_env AI_SEARCH_ENDPOINT "$AI_SEARCH_ENDPOINT"

# ── Stage 3 ───────────────────────────────────────────────────────────────
stage "A Genie space for test 5"
say "Test 5 checks that Genie answers a question as the person whose token asks it."
say "It needs a Genie space to ask. Later, ops/genie/deploy_space.py builds Strata's own space"
say "from code and adds its ID to your env file, and the probe asks that space from then on."
say ""
open_url "$DATABRICKS_HOST/genie"
step "Click New. When it asks for data, pick the table samples.nyctaxi.trips."
step "If it asks for a warehouse, pick the one from the last stage. Then create the space."
step "Copy the new space's address from your browser. It has /genie/rooms/ followed by the space ID."
ask_required GENIE_SPACE_ID "Paste the address or the space ID:"
write_env GENIE_SPACE_ID "$(genie_space_id "$GENIE_SPACE_ID")"

# ── Stage 4 ───────────────────────────────────────────────────────────────
stage "A browser sign-in for the Databricks command line"
say "The probes for tests 1 and 10 call a small Databricks app, and they use a browser sign-in"
say "for that. The Databricks command line keeps it under the profile name $PROFILE."
say ""
if databricks auth token -p "$PROFILE" >/dev/null 2>&1; then
  say "You are already signed in under the profile $PROFILE, so this stage has nothing to do."
else
  pause "Press Enter to open the sign-in page in your browser."
  if databricks auth login --host "$DATABRICKS_HOST" --profile "$PROFILE"; then
    say "You are signed in under the profile $PROFILE."
  else
    SKIPPED+=("Sign the command line in: databricks auth login --host $DATABRICKS_HOST --profile $PROFILE")
    warn "The sign-in did not finish. The probes for tests 1 and 10 need it."
  fi
fi

# ── Stage 5 ───────────────────────────────────────────────────────────────
stage "Your Microsoft Entra sign-in to Azure"
say "Foundry and the model deployments live in your Azure subscription. The Azure command"
say "line signs in with your Microsoft Entra account. Foundry evaluations need this sign-in too."
say ""
if ! az account show -o json >/dev/null 2>&1; then
  pause "Press Enter to sign in. A browser window opens."
  az login || warn "The Azure sign-in did not finish."
fi
account=$(az account show -o json 2>/dev/null || true)
if [[ -n "$account" ]]; then
  say "You are signed in. The subscription is \"$(printf '%s' "$account" | json_get 'd["name"]')\"."
  if ! confirm "Is this the subscription that holds the resource group $RESOURCE_GROUP?"; then
    az account list --query "[].{name:name, id:id}" -o table || true
    ask_required AZURE_SUBSCRIPTION "Paste the ID of the subscription to use:"
    az account set --subscription "$AZURE_SUBSCRIPTION" || warn "I could not switch to that subscription."
    account=$(az account show -o json 2>/dev/null || true)
  fi
fi
FOUNDRY_TENANT_ID=$(printf '%s' "$account" | json_get 'd["tenantId"]' || true)
if [[ -n "$FOUNDRY_TENANT_ID" ]]; then
  say "Your Microsoft Entra tenant ID is $FOUNDRY_TENANT_ID."
else
  warn "I could not read your tenant ID from the Azure command line."
  step "In the Azure portal, search for Microsoft Entra ID. The Overview page shows the tenant ID."
  ask_required FOUNDRY_TENANT_ID "Paste the tenant ID:"
fi
write_env FOUNDRY_TENANT_ID "$FOUNDRY_TENANT_ID"

# ── Stage 6 ───────────────────────────────────────────────────────────────
stage "The Foundry project $(setting names.foundry_project) on $FOUNDRY_RESOURCE"
say "Strata's agent, guardrails, evaluations and traces live in a Foundry project named"
say "$(setting names.foundry_project), on the Foundry resource $FOUNDRY_RESOURCE in the resource group $RESOURCE_GROUP."
say ""
open_url "https://ai.azure.com"
step "If the project $(setting names.foundry_project) already exists, open it."
step "If not, create a project named $(setting names.foundry_project). Under the advanced options, pick the resource group $RESOURCE_GROUP and the Foundry resource $FOUNDRY_RESOURCE. Create the resource with that name if it is missing."
step "Open the project's Overview page. It shows the project endpoint and the Azure OpenAI endpoint."
pause "Press Enter when the project's Overview page is open."
ask_with_default FOUNDRY_PROJECT_ENDPOINT "Paste the project endpoint." "$(example_value FOUNDRY_PROJECT_ENDPOINT)"
write_env FOUNDRY_PROJECT_ENDPOINT "${FOUNDRY_PROJECT_ENDPOINT%/}"
ask_with_default AZURE_OPENAI_ENDPOINT "Paste the Azure OpenAI endpoint." "$(example_value AZURE_OPENAI_ENDPOINT)"
write_env AZURE_OPENAI_ENDPOINT "$(openai_endpoint "$AZURE_OPENAI_ENDPOINT")"
AZURE_OPENAI_API_KEY=$(az cognitiveservices account keys list -g "$RESOURCE_GROUP" -n "$FOUNDRY_RESOURCE" \
  --query key1 -o tsv 2>/dev/null || true)
if [[ -n "$AZURE_OPENAI_API_KEY" ]]; then
  say "I read the resource's API key with the Azure command line, and I do not show it here."
else
  step "On the Overview page, copy the API key."
  ask_secret_required AZURE_OPENAI_API_KEY "Paste the API key. It stays hidden while you paste:"
fi
write_env AZURE_OPENAI_API_KEY "$AZURE_OPENAI_API_KEY"
put_scope_secret AZURE_OPENAI_API_KEY "$AZURE_OPENAI_API_KEY"

# ── Stage 7 ───────────────────────────────────────────────────────────────
stage "Four model deployments, each with a cap (test 8)"
say "Strata uses four model deployments. Each one gets a cap, because a budget only sends email."
say "This stage also answers day-one test 8, which asks whether the four models deploy within"
say "your quota."
say ""
open_url "https://ai.azure.com"
step "In the project, open Models + endpoints. Click Deploy model, then Deploy base model."
step "Deploy $(model_value agent) as $(setting caps.deployments.agent.deployment_type), named $(model_value agent). Under Customize, set the tokens-per-minute rate limit to $(with_commas "$(setting caps.deployments.agent.tokens_per_minute)")."
step "Deploy $(model_value draft) as $(setting caps.deployments.draft.deployment_type), named $(model_value draft), with a limit of $(with_commas "$(setting caps.deployments.draft.tokens_per_minute)") tokens per minute."
step "Deploy $(model_value batch) as $(setting caps.deployments.batch.deployment_type), named $(model_value batch). If the page offers an enqueued-token limit, set it to $(with_commas "$(setting caps.deployments.batch.enqueued_tokens)")."
step "Deploy $(model_value embed) as $(setting caps.deployments.embed.deployment_type), named $(model_value embed), with a limit of $(with_commas "$(setting caps.deployments.embed.tokens_per_minute)") tokens per minute."
note "Strata asks $(model_value embed) for $(with_commas "$(model_value embed dimensions)") dimensions in each request, so that deployment needs no setting for it."
note "Give each deployment the name shown. Strata reads the names from config/models.toml, so a deployment with another name means a change to that file."
note "If a deployment fails because the quota is too small, note what the page says. That answers test 8."
pause "Press Enter when you have tried all four."
deployments=$(az cognitiveservices account deployment list -g "$RESOURCE_GROUP" -n "$FOUNDRY_RESOURCE" -o json 2>/dev/null || true)
listed=$(printf '%s' "$deployments" | json_get '", ".join(x["name"] + " (" + x["sku"]["name"] + ")" for x in d)' || true)
if [[ -n "$listed" ]]; then
  say "Azure lists these deployments, with their type and capacity:"
  printf '%s' "$deployments" \
    | json_get '"\n".join("    " + x["name"] + "  " + x["sku"]["name"] + "  " + str(x["sku"].get("capacity", "")) for x in d)' \
    || true
  note "Azure shows capacity in thousands of tokens. For example, 100 on a Global Standard deployment means 100,000 tokens per minute."
  deploy_evidence="az cognitiveservices account deployment list returned $listed."
else
  deploy_evidence="az cognitiveservices account deployment list returned nothing, so this rests on what the portal showed."
fi
say ""
if [[ "$(test_status 8)" == "passed" ]]; then
  note "Test 8 passed on an earlier run, so there is nothing to ask."
elif confirm "Did all four deploy?"; then
  record_test 8 passed "All four models deployed within the subscription's quota." "$deploy_evidence"
else
  ask_required DEPLOY_PROBLEM "What did the page say? One line is enough:"
  record_test 8 failed "Not all four models deployed within the subscription's quota." \
    "The portal said: $DEPLOY_PROBLEM" "$deploy_evidence"
fi

# ── Stage 8 ───────────────────────────────────────────────────────────────
stage "An Azure budget with email alerts"
say "A budget sends you email as spend grows. It does not stop spend; the caps in the last"
say "stage do that."
say ""
open_url "https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/budgets"
step "If the page does not open on Budgets, search the portal for Budgets and open it."
step "Set the scope to your subscription, then click Add."
step "Name the budget $(setting names.budget). Set the reset period to Monthly and the amount to US\$$(setting caps.monthly_budget_usd)."
step "Add alert conditions for actual cost at $(setting caps.budget_alert_percents | paste -sd, - | sed 's/,/, /g; s/\(.*\), /\1 and /') percent, and for forecast cost at $(setting caps.budget_forecast_percent) percent."
step "Put your email address under alert recipients, then click Create."
pause "Press Enter when the budget is saved."
note "The caps probe checks that the budget exists and sends its alerts."

# ── Stage 9 ───────────────────────────────────────────────────────────────
stage "Application Insights for the app (test 10)"
say "Application Insights keeps the traces from the app and the agent. Test 10 checks that"
say "the app's traces arrive there."
say ""
open_url "https://portal.azure.com/#create/Microsoft.AppInsights"
step "Create an Application Insights resource in the resource group $RESOURCE_GROUP. Name it $(setting names.appinsights_resource), pick the region of $FOUNDRY_RESOURCE, and let it make a new Log Analytics workspace."
step "When it is ready, open it. Under Configure, open Usage and estimated costs, click Daily cap, and set it to $(setting caps.appinsights_daily_cap_gb) GB a day."
step "Go back to its Overview page and copy the connection string."
pause "Press Enter when you have copied the connection string."
ask_secret_required APPLICATIONINSIGHTS_CONNECTION_STRING "Paste the connection string. It stays hidden while you paste:"
write_env APPLICATIONINSIGHTS_CONNECTION_STRING "$APPLICATIONINSIGHTS_CONNECTION_STRING"
put_scope_secret APPLICATIONINSIGHTS_CONNECTION_STRING "$APPLICATIONINSIGHTS_CONNECTION_STRING"
step "Now connect it to Foundry. In the project at ai.azure.com, open Tracing in the left menu and connect $(setting names.appinsights_resource)."
pause "Press Enter when tracing is connected."

# ── Stage 10 ──────────────────────────────────────────────────────────────
stage "One Foundry evaluation after your Entra sign-in (test 9)"
if [[ "$(test_status 9)" == "passed" ]]; then
  say "Test 9 passed on an earlier run, so this stage has nothing to do."
else
  say "Foundry evaluations need a Microsoft Entra sign-in, which you made in stage 5. This"
  say "stage checks that one evaluation runs. That answers day-one test 9."
  say ""
  open_url "https://ai.azure.com"
  step "In the project, open Evaluation in the left menu and start a new evaluation."
  step "If the page offers a sample dataset, use it. Pick the groundedness evaluator and use $(model_value agent) as the judge."
  step "Submit it and wait until its status says Completed. This can take a few minutes."
  pause "Press Enter when the evaluation has finished or failed."
  if confirm "Did the evaluation finish with scores?"; then
    ask_required EVALUATION_LINK "Paste the evaluation's address from your browser:"
    record_test 9 passed "A Foundry evaluation ran after an Entra sign-in and returned scores." \
      "Evaluation: $EVALUATION_LINK"
  else
    ask_required EVALUATION_PROBLEM "What did the page say? One line is enough:"
    record_test 9 failed "A Foundry evaluation did not finish after an Entra sign-in." \
      "The portal said: $EVALUATION_PROBLEM"
  fi
fi

# ── Stage 11 ──────────────────────────────────────────────────────────────
stage "An outside reviewer in the workspace (test 6)"
status6=$(test_status 6)
if [[ "$status6" == "passed" ]]; then
  say "Test 6 passed on an earlier run, so this stage has nothing to do."
else
  say "Test 6 checks that someone outside your organization can join the workspace and open"
  say "the app. Reviewers on the panel will need this."
  say ""
  joined=1
  if [[ "$status6" != "waiting" ]]; then
    open_url "$DATABRICKS_HOST"
    step "Click your user icon, then Settings. Under Workspace admin, open Identity and access."
    step "Next to Users, click Manage. Click Add user, enter an outside email address you can check, such as a personal one, and click Add."
    step "Open a private browser window, sign in to $DATABRICKS_HOST as that person, and accept the invitation."
    pause "Press Enter when you have tried."
    if ! confirm "Could that person sign in to the workspace?"; then
      joined=0
      record_test 6 failed "An outside email could not join the workspace." \
        "The person invited an outside email, and it could not sign in to the workspace."
    fi
  fi
  if (( joined )); then
    app_url=""
    if (( DBX_OK )); then
      app_url=$(dbx apps get "$APP" -o json 2>/dev/null | json_get 'd.get("url") or ""' || true)
    fi
    if [[ -n "$app_url" ]]; then
      step "Give that person access to the app. In Compute, open Apps, open $APP, click Permissions, and add the person with Can use."
      step "Then, still signed in as that person, open $app_url"
      if confirm "Did the app open for that person?"; then
        record_test 6 passed "An outside email joined the workspace and opened the app." "App: $app_url"
      else
        record_test 6 failed "An outside email joined the workspace but could not open the app." "App: $app_url"
      fi
    else
      record_test 6 waiting \
        "An outside email joined the workspace. The app is not deployed yet, so that person could not open it." \
        "The probes deploy a small app named $APP. Run the wizard again after them to finish this test."
      say "The app is not deployed yet. After the probes deploy it, run this wizard again to finish test 6."
    fi
  fi
fi

# ── Stage 12 ──────────────────────────────────────────────────────────────
stage "Pay-as-you-go before $DEADLINE_LONG"
if dayone payg-done; then
  say "The subscription already moved to pay-as-you-go, so this stage has nothing to do."
else
  say "The free Azure credit ends on $DEADLINE_LONG. Before then, the subscription moves to"
  say "pay-as-you-go, so Strata keeps running. The caps and the budget limit what it can spend."
  say ""
  open_url "https://portal.azure.com/#view/Microsoft_Azure_Billing/SubscriptionsBladeV2"
  step "Open your subscription. On its Overview page, click Upgrade, and follow the steps."
  pause "Press Enter when the page is open."
  if confirm "Did you upgrade the subscription to pay-as-you-go just now?"; then
    dayone payg --status done --who "$(setting payg.who)" >/dev/null && note "I wrote the step as done in $RESULTS."
  else
    ask_with_default PAYG_WHO "Who will take this step? A name or a role is fine." "$(setting payg.who)"
    while true; do
      ask_required PAYG_DUE "On what date? Use the form YYYY-MM-DD, before $DEADLINE_LONG:"
      if dayone payg --status planned --who "$PAYG_WHO" --due "$PAYG_DUE" >/dev/null; then
        note "I wrote the planned step in $RESULTS."
        break
      fi
      PAYG_DUE=""
    done
  fi
fi

# ── Stage 13 ──────────────────────────────────────────────────────────────
stage "The day-one probes"
say "The probes answer tests 1, 2, 3, 4, 5, 8 and 10 and write each result in $RESULTS."
say "They take about 30 minutes, mostly while Databricks starts things. They deploy a small"
say "app named $APP and keep their test files in the schema $(setting names.schema)."
say "The results document lists everything they leave in the workspace."
say ""
if ! command -v uv >/dev/null 2>&1; then
  warn "The probes run with uv, and this computer does not have it yet. Install uv, then run this"
  warn "from the main checkout:"
  note "    bash ops/dayone/run-probes.sh --env-file .env"
elif confirm "Do you want to run them now?"; then
  bash "$ROOT/ops/dayone/run-probes.sh" --env-file "$ENV_FILE" || warn "Some probes did not pass. Their results say why."
else
  note "To run them later, run this from the main checkout:"
  note "    bash ops/dayone/run-probes.sh --env-file .env"
fi

finish
if [[ "$(test_status 6)" == "waiting" ]]; then
  note "Test 6 waits for the app. Run this wizard again after the probes to finish it."
fi
note "The day-one results are in $RESULTS."
printf '\n'
}

run_wizard "$@"; exit
