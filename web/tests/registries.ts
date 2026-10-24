// Reads the two registries a Data readiness number can come from, config/sources.toml and
// config/tools.toml, with Python's tomllib as the server does (the web app has no TOML reader), so
// tests check the page and the copy file against the files people edit.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const COLUMNS = ["coverage", "linked", "read_well", "fresh"] as const;
export type Column = (typeof COLUMNS)[number];

type Shown = { measure: string; counted_in: string; years?: string; projects?: string };
export type ReadinessRow = { id: string; label: string; covers?: string; checks?: Shown[] } & Partial<Record<Column, Shown>>;
type Fix = { measure: string; counted_in?: string; projects?: string; projects_counted_in?: string };
export type SourceRegistry = { sources: Record<string, { readiness?: ReadinessRow[]; fixes?: Fix[] }> };
export type ToolRegistry = { tools: Record<string, { readiness?: { ready_for: { row: string; measure: string; counted_in?: string } } }> };

export function readRegistry<T>(name: "sources.toml" | "tools.toml"): T {
  const path = fileURLToPath(new URL(`../../config/${name}`, import.meta.url));
  const read = spawnSync("python3", ["-c", "import json, sys, tomllib; print(json.dumps(tomllib.load(open(sys.argv[1], 'rb')), default=str))", path], {
    encoding: "utf8",
  });
  if (read.status !== 0) throw new Error(read.stderr);
  return JSON.parse(read.stdout) as T;
}

// Where the registries put each measure a number on /data can count, by "source/measure": the
// column of its row that shows it, or null for a check, a fix's own measure or a kind's Ready for
// measure that no column of its row shows, and the table it was counted in. A measure placed twice
// in different ways is a conflict, since its window is chosen by its name.
export type Placement = { column: Column | null; table: string | undefined };

export function placements(): { placed: Map<string, Placement>; conflicts: string[] } {
  const sources = readRegistry<SourceRegistry>("sources.toml").sources;
  const placed = new Map<string, Placement>();
  const conflicts: string[] = [];
  const place = (source: string, measure: string, placement: Placement) => {
    const key = `${source}/${measure}`;
    const was = placed.get(key);
    if (was && (was.column !== placement.column || was.table !== placement.table)) conflicts.push(key);
    placed.set(key, placement);
  };
  const rowSource = new Map<string, string>();
  const shownIn = new Map<string, Set<string>>();
  for (const [source, entry] of Object.entries(sources)) {
    const shown = new Set<string>();
    for (const row of entry.readiness ?? []) {
      rowSource.set(row.id, source);
      const inRow = new Set<string>();
      for (const column of COLUMNS) {
        const given = row[column];
        if (!given) continue;
        for (const measure of [given.measure, given.years].filter((name): name is string => Boolean(name))) {
          place(source, measure, { column, table: given.counted_in });
          inRow.add(measure);
        }
        // A document collection's projects, the slice's, which strata.gold.project holds (ticket 18).
        if (given.projects) {
          place(source, given.projects, { column: null, table: "strata.gold.project" });
          inRow.add(given.projects);
        }
      }
      for (const check of row.checks ?? []) {
        place(source, check.measure, { column: null, table: check.counted_in });
        inRow.add(check.measure);
      }
      shownIn.set(row.id, inRow);
      for (const measure of inRow) shown.add(measure);
    }
    for (const fix of entry.fixes ?? []) {
      if (!shown.has(fix.measure)) place(source, fix.measure, { column: null, table: fix.counted_in });
      if (fix.projects) place(source, fix.projects, { column: null, table: fix.projects_counted_in });
    }
  }
  for (const tool of Object.values(readRegistry<ToolRegistry>("tools.toml").tools)) {
    const readyFor = tool.readiness?.ready_for;
    if (!readyFor || shownIn.get(readyFor.row)?.has(readyFor.measure)) continue;
    place(rowSource.get(readyFor.row) ?? readyFor.row, readyFor.measure, { column: null, table: readyFor.counted_in });
  }
  return { placed, conflicts };
}
