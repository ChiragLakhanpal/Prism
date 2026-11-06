// Which talk and which part of it an address under /present names (ticket 47; the research talk, ticket 162). It lives
// apart from the deck, so the app's entry (web/src/main.tsx) can tell a deck address without loading the deck: the
// slides, their copy and the figures load only on /present.
//
// /present, /present/{n}, /present/page and /present/notes are Prism's own talk; the same four under /present/research
// are the deep research talk.
import { PLACES, type TalkKey } from "./talk";

export type DeckView = { talk: TalkKey } & ({ kind: "slides"; n: number | null } | { kind: "page" } | { kind: "notes" });

// The part of the deck an address names, or null for an address that is not the deck's.
export function deckView(pathname: string): DeckView | null {
  const path = pathname.replace(/\/+$/, "");
  const research = PLACES.research.base;
  const talk: TalkKey = path === research || path.startsWith(`${research}/`) ? "research" : "strata";
  const base = PLACES[talk].base;
  if (path === base) return { talk, kind: "slides", n: null };
  if (path === `${base}/page`) return { talk, kind: "page" };
  if (path === `${base}/notes`) return { talk, kind: "notes" };
  const rest = path.startsWith(`${base}/`) ? path.slice(base.length + 1) : "";
  return /^\d{1,4}$/.test(rest) ? { talk, kind: "slides", n: Number(rest) } : null;
}

// The slide the address shows now: presentation mode replaces the address as the slides move, so a deck that drops
// to the reading view and back, or a reading view opened at /present/{n}, keeps that slide.
export function slideInAddress(): number | null {
  const view = deckView(window.location.pathname);
  return view?.kind === "slides" ? view.n : null;
}
