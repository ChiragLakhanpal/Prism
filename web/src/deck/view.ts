// Which part of the deck an address under /present names (ticket 47). It lives apart from the deck, so the app's
// entry (web/src/main.tsx) can tell a deck address without loading the deck: the slides, their copy and the figures
// load only on /present.
export type DeckView = { kind: "slides"; n: number | null } | { kind: "page" } | { kind: "notes" };

// The part of the deck an address names, or null for an address that is not the deck's.
export function deckView(pathname: string): DeckView | null {
  const path = pathname.replace(/\/+$/, "");
  if (path === "/present") return { kind: "slides", n: null };
  if (path === "/present/page") return { kind: "page" };
  if (path === "/present/notes") return { kind: "notes" };
  const match = /^\/present\/(\d{1,4})$/.exec(path);
  return match ? { kind: "slides", n: Number(match[1]) } : null;
}

// The slide the address shows now: presentation mode replaces the address as the slides move, so a deck that drops
// to the reading view and back, or a reading view opened at /present/{n}, keeps that slide.
export function slideInAddress(): number | null {
  const view = deckView(window.location.pathname);
  return view?.kind === "slides" ? view.n : null;
}
