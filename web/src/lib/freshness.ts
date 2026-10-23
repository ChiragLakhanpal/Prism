// The data-freshness stamp's state (the 06 design brief, "The freshness stamp"). The app reads
// GET /api/freshness once per page load, with the viewer's own token, and keeps the answer across
// route changes, so the band never flickers. The server gives up after the thresholds file's
// app.stamp_timeout_seconds and answers with an error, which the stamp shows.
//
// After an error it tries again on the next route change, or when the tab becomes visible again,
// at most once a minute, and a retry says "Reading the data date" at once. A 401 or a 403 also
// puts an error alert above the title (web/src/App.tsx).
import type { Freshness } from "../components/BoxBand";
import { ApiError, getJson } from "./api";
import { formatDate } from "./format";
import { createStore } from "./store";

export type Problem = "no_identity" | "no_access" | null;
export type Stamp = { freshness: Freshness; problem: Problem };

// The static bar shows for the first second; then the stamp says it is reading the date.
const SLOW_MS = 1000;
const RETRY_MS = 60_000;

export const stamp = createStore<Stamp>({ freshness: { status: "loading" }, problem: null });
let lastRead = -Infinity;

async function read(slow: boolean) {
  lastRead = Date.now();
  stamp.set({ freshness: { status: "loading", slow }, problem: null });
  const timer = slow ? undefined : setTimeout(() => {
    const current = stamp.get().freshness;
    if (current.status === "loading") stamp.set({ freshness: { status: "loading", slow: true }, problem: null });
  }, SLOW_MS);
  try {
    const answer = await getJson<{ data_through: string | null }>("/api/freshness");
    stamp.set({
      freshness: answer.data_through
        ? { status: "ready", date: formatDate(answer.data_through, { style: "short" }) }
        : { status: "empty" },
      problem: null,
    });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 0;
    stamp.set({ freshness: { status: "error" }, problem: status === 401 ? "no_identity" : status === 403 ? "no_access" : null });
  } finally {
    clearTimeout(timer);
  }
}

// The read for this page load.
export function readStamp() {
  void read(false);
}

// A second try after an error, at most once a minute.
export function retryStamp() {
  if (stamp.get().freshness.status !== "error" || Date.now() - lastRead < RETRY_MS) return;
  void read(true);
}
