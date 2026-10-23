#!/usr/bin/env bash
#
# Run every day-one probe once, in order. Each probe writes its result in
# docs/day-one-results.md, in the same checkout as this script.
#
# Run it from the main checkout after the wizard:
#
#     bash ops/dayone/run-probes.sh --env-file .env
#
# Add --dry-run to use canned answers and write nothing. A probe that fails does not stop the
# others. The exit code is 0 only when every probe passed. The whole run takes about 30
# minutes, mostly while Databricks starts the app, the jobs and the AI Search endpoint.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The caps and Genie probes are quick. The hosts probe deploys the probe app, which the traces
# probe then reuses. The AI Search endpoint takes longest to start, so it runs last.
PROBES=(probe_caps.py probe_genie.py probe_hosts.py probe_traces.py probe_azure_from_job.py
        probe_parse_pad.py probe_ai_search.py)

env_file=""
dry_run=0
while (( $# )); do
  case "$1" in
    --env-file)
      if (( $# < 2 )); then printf 'Give --env-file the path of the env file.\n'; exit 2; fi
      env_file="$2"; shift 2 ;;
    --env-file=*) env_file="${1#--env-file=}"; shift ;;
    --dry-run) dry_run=1; shift ;;
    *) printf 'I do not know the option %s. Use --env-file PATH, and --dry-run if you want one.\n' "$1"; exit 2 ;;
  esac
done
if [[ -z "$env_file" ]] && (( ! dry_run )); then
  printf 'Pass the main checkout'"'"'s env file with --env-file, like this:\n'
  printf '    bash ops/dayone/run-probes.sh --env-file .env\n'
  exit 2
fi

args=()
(( dry_run )) && args+=(--dry-run)
[[ -n "$env_file" ]] && args+=(--env-file "$env_file")

failed=()
for probe in "${PROBES[@]}"; do
  printf '\nRunning %s.\n' "$probe"
  if ! uv run --script "$HERE/$probe" ${args[@]+"${args[@]}"}; then
    failed+=("$probe")
  fi
done

if (( dry_run )); then
  if (( ${#failed[@]} )); then
    printf '\nThese probes did not pass their dry run: %s. This was a dry run, so I wrote nothing.\n' "${failed[*]}"
    exit 1
  fi
  printf '\nEvery probe passed its dry run. This was a dry run, so I wrote nothing.\n'
  exit 0
fi
if (( ${#failed[@]} )); then
  printf '\nThese probes did not pass: %s. Their results in docs/day-one-results.md say why.\n' "${failed[*]}"
  exit 1
fi
printf '\nEvery probe passed. The results are in docs/day-one-results.md.\n'
