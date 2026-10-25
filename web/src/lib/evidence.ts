// The evidence drawer's state (ticket 14). The drawer is open when the address carries ?evidence=<id>,
// so a link reopens it; the answer is not in the address. The sources the stream sent are kept here, so
// a marker opens the drawer at once with no request; a drawer opened from a link asks the server.
//
// Opening a source marks it visited at once and records it for the viewer (POST /api/evidence/opened);
// the server records nothing in a preview. Closing goes back one entry when this session opened the
// drawer, so Back and Forward close and reopen it, and focus returns to the marker that opened it.
import type { EvidenceEvent } from "./answer";
import { postJson, getJson } from "./api";
import { address, navigate } from "./router";
import { createStore } from "./store";

export const PARAM = "evidence";

export const known = createStore<Record<string, EvidenceEvent>>({});
export const visited = createStore<ReadonlySet<string>>(new Set());
// When this page last showed each source in the drawer, in milliseconds, so a draft can count a source
// opened since it loaded at once, with no request (the 35 brief, section 4.5).
export const openedAt = createStore<Record<string, number>>({});

// Where the open drawer came from: the answer (its run's serial, web/src/lib/answer.ts), the sentence
// whose marker opened it, and that marker, for the claim block, the switcher and focus on close. A
// drawer opened from a link has none. The serial keeps a later answer's sentence from being paired
// with a source an earlier answer opened (CLAUDE.md rule 2). The marker's top in the window when it was
// clicked lets a draft put the marker back where the reader saw it after the notes reflow; a switch between
// a sentence's sources has none, since nothing reflows. The fallback takes focus on close when the marker is
// gone, such as section 1's heading when a rerun of find_comparables redrew the dot that opened the drawer
// (the 15 brief, section 8). A lesson's evidence card or Source chip, which is no answer's sentence, gives
// the quote's place in the passage itself (highlight, from the server), so the drawer opens with the quote
// it showed highlighted (the 29 brief, section 8).
export type Origin = {
  id: string;
  serial: number | null;
  sentence: number | null;
  marker: HTMLElement | null;
  runId: string | null;
  top: number | null;
  fallback?: HTMLElement | null;
  highlight?: [number, number] | null;
  // A package opened from a quantile dot's list names that list, so the drawer offers a way back to it; the
  // list, shown again, names the package it came back from, which takes focus (ticket 15).
  list?: { id: string; count: number } | null;
  entry?: string | null;
  // Where a timeline's event mark opened it (ticket 23): "From the timeline" and the event with its date, above the
  // passage or record that dates it, as "From the answer" sits above a sentence's source.
  context?: { lead: string; line: string } | null;
};
export const origin = createStore<Origin | null>(null);

// Whether this session pushed the open drawer's history entry, so closing can go back to the page.
let pushed = false;

// A marker or a number asks the drawer to take focus; a switcher tab does not. The drawer takes each
// request once.
export const focusRequests = createStore(0);
let handledFocus = 0;

export function takeFocusRequest(): boolean {
  const asked = focusRequests.get();
  if (asked === handledFocus) return false;
  handledFocus = asked;
  return true;
}

export function remember(event: EvidenceEvent) {
  known.set((all) => ({ ...all, [event.id]: event }));
}

export function evidenceIn(search: string): string | null {
  const id = new URLSearchParams(search).get(PARAM);
  return id && id.trim() ? id : null;
}

// The address with the drawer open at this source, keeping view, asof and lang.
export function evidenceHref(id: string, here: { pathname: string; search: string } = address.get()): string {
  const params = new URLSearchParams(here.search);
  params.set(PARAM, id);
  return `${here.pathname}?${params.toString()}`;
}

// The address without ?evidence=: the route. Opening or closing the drawer is the only change to the
// address that is not a route change, so it neither scrolls the page nor moves focus to the h1.
export function routeOf({ pathname, search }: { pathname: string; search: string } = address.get()): string {
  const params = new URLSearchParams(search);
  params.delete(PARAM);
  const rest = params.toString();
  return rest ? `${pathname}?${rest}` : pathname;
}

function withoutEvidence(): string {
  return routeOf();
}

function markVisited(id: string) {
  visited.set((all) => (all.has(id) ? all : new Set([...all, id])));
}

// The source the open drawer last recorded, so one opening writes one row even when React's
// StrictMode runs the drawer's effects twice in development.
let recorded: string | null = null;

// Record that the viewer opened a source: once now, and once more if the write fails.
export function recordOpened(id: string, runId: string | null) {
  markVisited(id);
  openedAt.set((all) => ({ ...all, [id]: Date.now() }));
  if (id === recorded) return;
  recorded = id;
  const params = new URLSearchParams(address.get().search);
  const body = { evidence_id: id, run_id: runId, route: address.get().pathname, view: params.get("view") ?? "staff" };
  postJson<{ recorded: boolean }>("/api/evidence/opened", body).catch(() =>
    postJson("/api/evidence/opened", body).catch((error: unknown) => console.warn("I could not record an opened source.", error)),
  );
}

// Which of an answer's sources the viewer opened before, so their markers land visited.
export async function loadVisited(ids: string[]) {
  if (ids.length === 0) return;
  const query = ids.map((id) => `id=${encodeURIComponent(id)}`).join("&");
  try {
    const { opened } = await getJson<{ opened: string[] }>(`/api/evidence/opened?${query}`);
    for (const id of opened) markVisited(id);
  } catch {
    // The markers stay as they are; nothing the viewer sees depends on this.
  }
}

// Open the drawer at a source: from a marker, a number or a switcher tab. A switcher tab replaces the
// entry; anything else adds one, on the same page, so Back closes the drawer.
export function openEvidence(id: string, from: Omit<Origin, "id" | "top"> | null, options: { replace?: boolean; focus?: boolean } = {}) {
  const marker = from?.marker;
  const top = !options.replace && marker && marker.getClientRects().length > 0 ? marker.getBoundingClientRect().top : null;
  origin.set(from ? { id, ...from, top } : null);
  if (options.focus ?? true) focusRequests.set((count) => count + 1);
  const open = evidenceIn(address.get().search);
  if (open === id) return;
  if (options.replace || open) {
    navigate(evidenceHref(id), { replace: true });
  } else {
    navigate(evidenceHref(id), { samePage: true });
    pushed = true;
  }
}

// Close the drawer: back one entry when this session opened it, or the same address without it.
export function closeEvidence() {
  if (pushed) {
    pushed = false;
    window.history.back();
  } else {
    navigate(withoutEvidence(), { replace: true });
  }
}

// The drawer closed by any route (Back included): forget that this session opened it.
export function drawerClosed() {
  pushed = false;
  recorded = null;
}

// An answer is going away (a new question, or "Close the answer"): close the drawer it opened. A
// drawer opened from a link, or from another answer, stays.
export function closeDrawerOf(serial: number) {
  const from = origin.get();
  if (!from || from.serial !== serial) return;
  origin.set(null);
  if (evidenceIn(address.get().search) !== null) closeEvidence();
}
