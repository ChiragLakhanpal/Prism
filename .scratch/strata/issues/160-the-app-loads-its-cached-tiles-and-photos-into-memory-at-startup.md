# 160: The App loads its cached tiles and photos into memory at startup, so the first view is as fast as the second

**What to build:** After the fifth deploy of the Prism night (November 6, 2026, 00:25 PST) the tile route (`src/strata/server/research_tiles.py`, ticket 158) fills the App's memory one tile at a time on each tile's first request, from `strata.ops.research_cache` at about 1.5 seconds a read, and the photo route (`src/strata/server/field_photos.py`, ticket 150) reads the table and the volume on every request at 2.4 to 3 seconds a photo, 10 seconds cold, keeping nothing in memory. The ops agent's warm-up ran in its own process, not the App's, and the App's address accepts only OAuth tokens, so nothing can warm it from outside. The first person to open a project's Deep research tab in the morning, the panel included, pays the cold cost: 36 to 54 tile reads and two or three photo reads. Two changes, server only:

1. **Tiles at startup.** When the App starts (and once per process, on the first tile request if startup did not run), the tile route loads every cached tile in one query (`SELECT url, body FROM strata.ops.research_cache WHERE source_key = 'sentinel2_mosaic'`, about 162 rows and 5 MB tonight; cap the load at a configured byte budget, `research.tile_memory_bytes` in `config/thresholds.toml`, 64 MB, with the newest rows first) into the memory cache it already has, as the App's own identity, in a background thread so the App answers its health check at once. A tile not in memory still follows the route's path (cache table, then EOX). Log one line with the count loaded and the seconds it took.
2. **Photos in memory.** The photo file route keeps each photo's bytes in a per-process memory cache keyed by photo id after the first read (bounded by `research.photo_memory_bytes`, 64 MB, oldest out), and at startup loads every photo of every team in the same background thread (12 files tonight). The access check (`access.may_read`) runs on every request before any bytes are served, exactly as now, so the cache changes nothing about who may see a photo; a photo deleted or replaced through the store drops out of the cache (the store's delete and create paths call a `forget(photo_id)` hook). `Cache-Control: private, no-store` stays.

Tests: the tile load at startup fills memory from a fake cache table and the route then serves without a query (count the engine's calls); the byte budget stops the load; a photo's second read makes no store call and the access check still runs (a viewer outside the team gets 403 on a cached photo); a forgotten photo is read again. Keep the gate under 180 seconds.

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD (929a7140 or later). Ticket 159 is changing the web's progress rail in parallel; keep your edits to the two server modules, `config/thresholds.toml`, the store's hooks and the tests. Essentials only, no review rounds; the user is asleep and the demo is at 8 am, so report within 40 minutes with whatever is done and a plain list of what is not. Commit with plain-English messages and no trailers. Do not change ticket files, docs/STATUS.md or anything under .scratch. Report: branch and worktree, each change with its evidence, the gate's time, and the workspace step (a redeploy of the App; after it, the App's log line with the counts loaded, if the ops agent can read it).

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** app
**Phase:** P5
**Design review:** no

- [ ] On startup the App loads its cached tiles and photos into memory in one background pass, within a byte budget from the thresholds (tests, the log line).
- [ ] A second read of a tile or a photo makes no table, volume or EOX call, and the photo access check still runs on every request (tests).
- [ ] The gate passes under 180 seconds on the worktree.

## Comments

- November 6, 2026, orchestrator: opened at 00:42 PST from the fifth deploy's warm-up report; ships in the sixth deploy of the Prism night with ticket 159.
