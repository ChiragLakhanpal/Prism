// Moving between the app's pages without reloading: a click on a link to one of the app's own
// addresses, and the browser's back and forward buttons, change the address and this store, and
// the app shows the page that web/src/routes.ts matches. Links stay plain <a href> elements, so
// they open in a new tab, copy and read like links. /api and /gallery addresses, links with a
// target or a download, a modifier key, and links to another part of the same page load as usual.
import { createStore } from "./store";

export type Address = {
  pathname: string;
  search: string;
  // How many times the address changed since the page loaded; 0 on the first page.
  moves: number;
};

const here = (moves: number): Address => ({ pathname: window.location.pathname, search: window.location.search, moves });

export const address = createStore<Address>(here(0));

export function navigate(to: string, options: { replace?: boolean } = {}) {
  if (options.replace) {
    window.history.replaceState(window.history.state, "", to);
    address.set(here(address.get().moves));
    return;
  }
  window.history.pushState(null, "", to);
  address.set(here(address.get().moves + 1));
}

const LOADS_AS_USUAL = /^\/(api|gallery)(\/|$)/;

function onClick(event: MouseEvent) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = (event.target as Element | null)?.closest?.("a");
  if (!(link instanceof HTMLAnchorElement) || !link.href || link.target || link.hasAttribute("download")) return;
  const to = new URL(link.href);
  if (to.origin !== window.location.origin || LOADS_AS_USUAL.test(to.pathname)) return;
  if (to.pathname === window.location.pathname && to.search === window.location.search && to.hash) return;
  event.preventDefault();
  navigate(to.pathname + to.search + to.hash);
}

function onPopState() {
  address.set(here(address.get().moves + 1));
}

// Starts listening for clicks and history moves; the returned function stops it.
export function startRouter(): () => void {
  document.addEventListener("click", onClick);
  window.addEventListener("popstate", onPopState);
  return () => {
    document.removeEventListener("click", onClick);
    window.removeEventListener("popstate", onPopState);
  };
}
