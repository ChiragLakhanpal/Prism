// Start here as a to-do list (ticket 114): the six examples Home's strip offers (config/examples.toml's
// [[start_here]]) follow the person to every page. Home keeps the links its answer gave (start_here.links of GET
// /api/home) in local storage under strata.startHere, with the keys of the examples the person followed from the strip
// or the sidebar, so other pages need no request. Every read and write is inside try/catch: without storage nothing is
// kept, and no page shows the list. The sidebar shows it only while GET /api/me says the strip shows (lib/home.ts's
// startHereVisible), so Remove takes it off every page at once.
import type { HomeAnswer } from "./home";
import { createStore } from "./store";

export const START_HERE_KEY = "strata.startHere";
// The strip's heading on Home, where "All six done" leads, and Remove stays.
export const START_HERE_ANCHOR = "start-here";
export const START_HERE_HREF = `/#${START_HERE_ANCHOR}`;

export type StartHereLink = HomeAnswer["start_here"]["links"][number];
export type StartHereList = { links: StartHereLink[]; done: string[] };

// Only an address inside the app is kept as a link.
const ownAddress = (href: unknown): href is string => typeof href === "string" && href.startsWith("/") && !href.startsWith("//");

function linkOf(value: unknown): StartHereLink | null {
  if (typeof value !== "object" || value === null) return null;
  const { key, href, pid } = value as Record<string, unknown>;
  if (typeof key !== "string" || !ownAddress(href) || !(pid === null || typeof pid === "string")) return null;
  return { key, href, pid };
}

function read(): StartHereList | null {
  try {
    const raw = window.localStorage.getItem(START_HERE_KEY);
    if (!raw) return null;
    const kept = JSON.parse(raw) as { links?: unknown; done?: unknown };
    if (!Array.isArray(kept.links) || !Array.isArray(kept.done)) return null;
    const links = kept.links.map(linkOf);
    if (links.some((link) => link === null)) return null;
    return { links: links as StartHereLink[], done: kept.done.filter((key): key is string => typeof key === "string") };
  } catch {
    return null;
  }
}

export const startHereList = createStore<StartHereList | null>(read());

function save(next: StartHereList) {
  try {
    window.localStorage.setItem(START_HERE_KEY, JSON.stringify(next));
  } catch {
    // Without storage the list is not kept, and no page shows it.
    return;
  }
  startHereList.set(next);
}

// Home's answer gave its links: keep them, with the done keys that still name one of them.
export function keepLinks(links: StartHereLink[]) {
  const kept = startHereList.get();
  const keys = new Set(links.map((link) => link.key));
  const done = (kept?.done ?? []).filter((key) => keys.has(key));
  if (kept && JSON.stringify(kept) === JSON.stringify({ links, done })) return;
  save({ links, done });
}

// The person followed an example from the strip or the sidebar.
export function markDone(key: string) {
  const kept = startHereList.get();
  if (!kept || kept.done.includes(key) || !kept.links.some((link) => link.key === key)) return;
  save({ ...kept, done: [...kept.done, key] });
}

// How far the person is: the examples followed, of all of them, and the first one not followed yet, in the strip's
// order (null once all are done).
export function progressOf(list: StartHereList): { done: number; total: number; upcoming: StartHereLink | null } {
  const followed = list.links.filter((link) => list.done.includes(link.key));
  return { done: followed.length, total: list.links.length, upcoming: list.links.find((link) => !list.done.includes(link.key)) ?? null };
}
