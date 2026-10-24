// A page's own browser tab title, such as a draft's "Review notes on the ... plan of Oct 9, 2026", which
// only the page knows once its data has loaded. App.tsx prefers it over the route's generic title while
// the address is still the page that set it, so a later route change needs no clean-up, and App's own
// effect, which runs after the page's, can't write the generic title over it.
import { createStore } from "./store";

export const pageTitle = createStore<{ path: string; title: string } | null>(null);

export function setPageTitle(title: string) {
  pageTitle.set({ path: window.location.pathname, title });
}
