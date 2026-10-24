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

// Where the open drawer came from: the sentence whose marker opened it, and that marker, for the
// claim block, the switcher and focus on close. A drawer opened from a link has none.
export type Origin = { id: string; sentence: number | null; marker: HTMLElement | null; runId: string | null };
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

function withoutEvidence(): string {
  const { pathname, search } = address.get();
  const params = new URLSearchParams(search);
  params.delete(PARAM);
  const rest = params.toString();
  return rest ? `${pathname}?${rest}` : pathname;
}

function markVisited(id: string) {
  visited.set((all) => (all.has(id) ? all : new Set([...all, id])));
}

// Record that the viewer opened a source: once now, and once more if the write fails.
export function recordOpened(id: string, runId: string | null) {
  markVisited(id);
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
export function openEvidence(id: string, from: Omit<Origin, "id"> | null, options: { replace?: boolean; focus?: boolean } = {}) {
  origin.set(from ? { id, ...from } : null);
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
}
