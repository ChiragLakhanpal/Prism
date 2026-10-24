// The app's routes (docs/PLAN.md section 8; the 06 and 10 design briefs): which page an address
// opens, the tab it selects, the values it takes from the address, and where the page's one link
// goes. Every page's words are in copy.pages under the same key. /present belongs to ticket 47;
// until then it is not found, like any other unknown address.
//
// Ticket 10 adds a project's Procurement tab (/projects/:pid/procurement, which /projects/:pid shows
// until ticket 21 adds Summary) and Check a plan (/projects/:pid/procurement/:agencyId/:version, or
// with no version for the agency's latest plan; :version is the plan's ISO date). Ticket 35 adds the
// Drafts tab's pages: /drafts, /drafts/new and /drafts/:draftId. Ticket 29 adds the Lessons tab's
// Waiting for review (/lessons/review) and one item's review page (/lessons/review/:itemId).
import type { copy } from "./copy";
import type { Section } from "./components/TopNav";

export type PageKey = keyof typeof copy.pages;

export type Match = {
  key: PageKey;
  // The tab the page selects: sub-routes select their parent, Home and not-found pages none.
  section?: Section;
  // {pid}, {stepRef}, {id}, {agencyId} and {version}, as the address gives them.
  values: Record<string, string>;
  // Where the page's link goes, if it has one.
  linkHref?: string;
  // The address to show instead, such as /projects/P130164 for /projects/p130164.
  canonical?: string;
};

const PROJECT_ID = /^[Pp]\d{6}$/;
const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

// A real calendar day written as an ISO date, such as 2026-10-09.
export function isDay(text: string): boolean {
  if (!DAY.test(text)) return false;
  const date = new Date(`${text}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(text);
}

// The Data tab's sub-pages under /data (the 16 design brief, section 2): Data readiness is /data.
export const DATA_PAGES = { dataSources: "sources", dataHow: "how-strata-works" } as const;
export const DATA_HREF = { data: "/data", dataSources: "/data/sources", dataHow: "/data/how-strata-works" } as const;

// Where a coverage line links (DESIGN.md section 5): Data readiness, showing only the sources behind
// the answer, by their source registry keys, and the tool that wrote the line, such as
// find_comparables, which the page turns into words from the copy file.
export function dataReadinessHref(sources: string[], from: string): string {
  const query = new URLSearchParams({ sources: sources.join(","), from });
  return `${DATA_HREF.data}?${query.toString().replaceAll("%2C", ",")}`;
}

function page(key: PageKey, section?: Section, values: Record<string, string> = {}): Match {
  return { key, section, values, linkHref: LINKS[key]?.(values) };
}

const LINKS: Partial<Record<PageKey, (values: Record<string, string>) => string>> = {
  home: () => "/data",
  packages: () => "/data",
  package: () => "/packages",
  activity: (values) => `/projects/${values.pid}`,
  document: (values) => `/projects/${values.pid}`,
  lessons: () => "/data",
  drafts: () => "/packages",
  notFound: () => "/",
  notAProject: () => "/projects",
};

function decode(part: string): string | null {
  try {
    return decodeURIComponent(part);
  } catch {
    return null;
  }
}

export function matchRoute(pathname: string): Match {
  const raw = pathname.replace(/\/+$/, "").split("/").slice(1);
  const parts = raw.map(decode);
  if (parts.some((part) => part === null || part === "")) return page("notFound");
  const [first, second, third, fourth, ...rest] = parts as string[];

  if (parts.length === 0) return page("home");
  if (first === "packages" && parts.length === 1) return page("packages", "packages");
  if (first === "packages" && parts.length === 2) return page("package", "packages", { id: second });
  if (first === "lessons" && parts.length === 1) return page("lessons", "lessons");
  // Ticket 29: the lesson review queue and one item's review page, for lesson reviewers.
  if (first === "lessons" && second === "review" && parts.length === 2) return page("lessonsQueue", "lessons");
  if (first === "lessons" && second === "review" && parts.length === 3) return page("lessonReview", "lessons", { itemId: third });
  if (first === "drafts" && parts.length === 1) return page("drafts", "drafts");
  // Ticket 35: writing a draft (/drafts/new?kind=...), and a draft by its id. PLAN.md section 8 does not
  // list these two routes; "new" is never a draft's id.
  if (first === "drafts" && parts.length === 2 && second === "new") return page("draftNew", "drafts");
  if (first === "drafts" && parts.length === 2) return page("draft", "drafts", { id: second });
  if (first === "data" && parts.length === 1) return page("data", "data");
  if (first === "data" && parts.length === 2 && second === DATA_PAGES.dataSources) return page("dataSources", "data");
  if (first === "data" && parts.length === 2 && second === DATA_PAGES.dataHow) return page("dataHow", "data");
  if (first !== "projects") return page("notFound");
  if (parts.length === 1) return page("projects", "projects");

  if (!PROJECT_ID.test(second)) return page("notAProject");
  const pid = second.toUpperCase();
  let match: Match;
  if (parts.length === 2 || (third === "procurement" && parts.length === 3)) match = page("project", "projects", { pid });
  else if (third === "procurement" && rest.length <= 1) {
    const [version] = rest;
    if (version !== undefined && !isDay(version)) return page("notFound");
    match = page("checkPlan", "projects", { pid, agencyId: fourth, ...(version ? { version } : {}) });
  } else if (third === "packages" && fourth && rest.length === 0) match = page("activity", "projects", { pid, stepRef: fourth });
  else if (third === "documents" && fourth && rest.length === 0) match = page("document", "projects", { pid, doc: fourth });
  else return page("notFound");
  if (pid !== second) match.canonical = ["", ...raw.slice(0, 1), pid, ...raw.slice(2)].join("/");
  return match;
}

// A copy template with its {name} slots filled, for the browser tab's title.
export function fill(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (slot, name: string) => values[name] ?? slot);
}
