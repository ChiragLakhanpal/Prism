# 77: The demo-ready check leaves a healthy App running, and waits long enough when it must restart one

**What to build:** `ops/demo/ready.py` (ticket 48) restarts a running App on purpose, because an app stops 24 hours after each start or deploy (its docstring, step 1), and then waits for GET /api/health for at most `[demo_ready] health_timeout_seconds` = 300 in `config/thresholds.toml`. On October 26, 2026 the second session's first run restarted the App at 09:32 UTC and failed step 1: "The app did not answer GET /api/health within 300 seconds. The last try said: HTTP Error 502: Bad Gateway". A probe beside the second run measured the restart: health 200 at 09:39:47, 503 from 09:40:02, 502 from 09:42:40 and 200 again at 09:48:12, so the App needs about eight and a half minutes after a restart, since the runtime installs `ops/app/requirements.txt` on every start. Run on demo day as README says, the check would take the App down for nine minutes and then report a failure. Change step 1: restart a running App only when its last start or deploy, as the Apps API reports it, is older than `[demo_ready] restart_after_hours` (a new value; 12, so a run on the morning of the demo restarts an App started the day before and leaves one started that morning alone); start a stopped App as today; in both cases wait up to `health_timeout_seconds`, raised to 900 with a comment that names the measured restart; and say in the output which of the three happened and why. Add tests with the fake workspace for the three cases and for the timeout message. README's "Before a demo" section says when the check restarts the App.

Read first: `ops/demo/ready.py` (step 1, the app section), its tests (the fake workspace), `config/thresholds.toml` [demo_ready], README's "Before a demo" section, the catch-up file's blocks 48-2 and 48-3 of October 26.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] With the fake workspace, a running App started less than `restart_after_hours` ago is left alone and reported as such; one started earlier is restarted; a stopped App is started; each case waits for health up to `health_timeout_seconds`, and the timeout message names the last answer.
- [ ] `config/thresholds.toml` holds `restart_after_hours` and `health_timeout_seconds = 900` with comments that name the measured restart time and its source; README's "Before a demo" section says when the check restarts the App.
- [ ] The second session's next run of the check on a healthy App leaves it running and passes step 1 (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 02:53 PDT from the second session's two runs, recorded under 48-2 and 48-3. On the demo-day path: a clean demo day starts with this check.
