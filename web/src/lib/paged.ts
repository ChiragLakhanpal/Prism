// A list the server searches and pages, such as All projects or a project's Packages (ticket 21). Its
// query and page live in the address, so a search can be shared and Back works. While the next answer is
// on its way, the rows already shown stay; after 400 ms with no answer the page says it is searching, so a
// fast answer never flashes. Typing replaces the address in place (quietly, so focus and the scroll stay),
// and a page link adds a history entry.
import { useEffect, useRef, useState } from "react";
import { useLoad, type Load } from "./load";
import { address, navigate } from "./router";
import { useStore } from "./store";

export const SEARCHING_AFTER_MS = 400;

// The query and page an address asks for, under the given parameter names.
export function pageParams(search: string, names: { query: string; page: string }) {
  const params = new URLSearchParams(search);
  const asked = Number(params.get(names.page) ?? "1");
  return { query: params.get(names.query) ?? "", page: Number.isInteger(asked) && asked >= 1 ? asked : 1 };
}

// The address with the query and page set, keeping every other parameter, such as ?asof= or ?view=. An
// empty query and the first page are left out.
export function pageHref(names: { query: string; page: string }, query: string, page: number, here = address.get()): string {
  const params = new URLSearchParams(here.search);
  params.delete("evidence");
  if (query) params.set(names.query, query);
  else params.delete(names.query);
  if (page > 1) params.set(names.page, String(page));
  else params.delete(names.page);
  const rest = params.toString();
  return rest ? `${here.pathname}?${rest}` : here.pathname;
}

export function usePagedList<T extends { page: number; pages: number }>(
  api: string,
  names: { query: string; page: string },
  extra: Record<string, string> = {},
) {
  const here = useStore(address);
  const { query, page } = pageParams(here.search, names);
  const params = new URLSearchParams(extra);
  if (query) params.set("q", query);
  if (page > 1) params.set("page", String(page));
  const rest = params.toString();
  const [load, retry] = useLoad<T>(rest ? `${api}?${rest}` : api);
  const last = useRef<T | null>(null);
  if (load.status === "ready") last.current = load.data;
  const [searching, setSearching] = useState(false);
  useEffect(() => {
    if (load.status !== "loading") {
      setSearching(false);
      return;
    }
    const timer = setTimeout(() => setSearching(true), SEARCHING_AFTER_MS);
    return () => clearTimeout(timer);
  }, [load.status, query, page]);

  // A page past the last is replaced with the last page the server gave.
  useEffect(() => {
    if (load.status === "ready" && load.data.pages > 0 && load.data.page !== page) {
      navigate(pageHref(names, query, load.data.page), { replace: true, quiet: true });
    }
  }, [load]);

  const search = (next: string) => navigate(pageHref(names, next.trim(), 1), { replace: true, quiet: true });
  const href = (to: number) => pageHref(names, query, to);
  // The rows to show: this answer's, or the last answer's while the next is on its way.
  const shown: T | null = load.status === "ready" ? load.data : load.status === "loading" ? last.current : null;
  return { load: load as Load<T>, retry, query, page, shown, waiting: load.status === "loading" && shown !== null, searching, search, href };
}
