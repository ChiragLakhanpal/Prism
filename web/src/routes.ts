// The app's routes (docs/PLAN.md section 8; the 06 and 10 design briefs): which page an address
// opens, the tab it selects, the values it takes from the address, and where the page's one link
// goes. Every page's words are in copy.pages under the same key. /present belongs to ticket 47;
// until then it is not found, like any other unknown address.
//
// Ticket 10 adds a project's Procurement tab and Check a plan (/projects/:pid/procurement/:agencyId/:version,
// or with no version for the agency's latest plan; :version is the plan's ISO date). Ticket 21 makes the
// project page the hub: /projects/:pid is its Summary (/projects/:pid/summary is rewritten to it), with
// /projects/:pid/procurement and /projects/:pid/documents beside it, and the source view at
// /projects/:pid/documents/:doc, where :doc is a document's key such as icr-2019-10-10. Ticket 12 builds the
// package workspace at /packages/:id, where :id is the package's STEP reference. Ticket 35 adds the
// Drafts tab's pages: /drafts, /drafts/new and /drafts/:draftId. Ticket 29 adds the Lessons tab's
// Waiting for review (/lessons/review) and one item's review page (/lessons/review/:itemId). Ticket 32 adds
// Passage reports (/lessons/reports, /lessons/reports/:groupId) and Judging (/lessons/judging,
// /lessons/judging/:queryId).
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
  // The address named a page that is gone (RETIRED_DATA_PAGES below), so the section its #fragment named is gone
  // too: the address shown instead keeps the query and drops the fragment.
  retired?: boolean;
  // The page a set of tabs shares, such as a project's Summary, Procurement and Documents: the app keeps
  // that page in place when you move between its tabs, so its header and tab row stay where they are.
  frame?: string;
  // The section the page belongs to in a view that has no section of its own: the plan check belongs to Packages,
  // and to Projects in the public view, which has no Packages (ticket 100; DESIGN.md section 5, Plan check table).
  fallbackSection?: Section;
};

// The section the sidebar lights for a page, in a view that has these sections: the page's own, or its fallback when
// the view lacks it (ticket 100). Until the view's sections are known, the page's own.
export function litSection(match: Match, sections: readonly string[] | null): Section | undefined {
  if (!match.section || !sections || sections.includes(match.section)) return match.section;
  return match.fallbackSection ?? match.section;
}

// The pages on the workspace layout that draw an answer asked on them in their own work columns, above their head and
// beside their side panel (DESIGN.md section 4, Page layouts, Workspace; Workspace.tsx's answer slot, read through
// AnswerSlot.tsx). Every other page shows the answer at the top of the page column. Home is the first (ticket 98);
// each ticket that moves a page onto the workspace adds its key here.
export const ANSWER_IN_PAGE: ReadonlySet<PageKey> = new Set<PageKey>(["home"]);

// A project page's tabs. Their order lives in one place, the copy file (copy.projectPage.tab), which the tab row reads
// (ticket 99); here each tab has its address. Ticket 23 added "timeline" and ticket 22 "connections".
export type ProjectTab = keyof typeof copy.projectPage.tab;
export const TAB_PATH: Record<ProjectTab, string> = {
  summary: "",
  procurement: "/procurement",
  timeline: "/timeline",
  documents: "/documents",
  connections: "/connections",
};

const PROJECT_ID = /^[Pp]\d{6}$/;
// A planned package's id (src/strata/server/packages.py): pkg- and twelve lowercase hex digits or digits.
export const PLANNED_ID = /^pkg-[0-9a-f]{12}$/;
const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

// A real calendar day written as an ISO date, such as 2026-10-09.
export function isDay(text: string): boolean {
  if (!DAY.test(text)) return false;
  const date = new Date(`${text}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(text);
}

// The Data tab's sub-pages under /data (the 16 design brief, section 2): Data readiness is /data.
export const DATA_PAGES = { dataSources: "sources" } as const;
export const DATA_HREF = { data: "/data", dataSources: "/data/sources" } as const;
// Addresses under /data that were pages once, and the page each opens now, through a replace, so an old link lands
// somewhere true and Back never returns to it. Ticket 97: How Strata works left Data, because the deck at /present
// shows its figures and the refusal window under an answer lists what I turn down.
const RETIRED_DATA_PAGES: Readonly<Record<string, string>> = { "how-strata-works": DATA_HREF.data };

// Where a coverage line links (DESIGN.md section 5): Data readiness, showing only the sources behind
// the answer, by their source registry keys, and the tool that wrote the line, such as
// find_comparables, which the page turns into words from the copy file. An empty list is left out,
// never sent as an empty sources=.
export function dataReadinessHref(sources: string[], from: string): string {
  const query = new URLSearchParams();
  if (sources.length > 0) query.set("sources", sources.join(","));
  query.set("from", from);
  return `${DATA_HREF.data}?${query.toString().replaceAll("%2C", ",")}`;
}

// Where section 3's empty state on a package's page links when no completion report was read (RisksSection.tsx, from
// the server's coverage line): Data readiness for the sources its risks draw on, find_comparables' and get_lessons' in
// config/tools.toml. The Lessons library's empty card links there too (ticket 114), before any package is open;
// web/tests/lessons-page.spec.ts checks it against the server's recorded answer for section 3.
export const RISKS_READINESS_HREF = dataReadinessHref(["notices", "awards", "documents", "projects"], "package_risks");

function page(key: PageKey, section?: Section, values: Record<string, string> = {}): Match {
  return { key, section, values, linkHref: LINKS[key]?.(values) };
}

const LINKS: Partial<Record<PageKey, (values: Record<string, string>) => string>> = {
  packages: () => "/data",
  activity: (values) => `/projects/${values.pid}`,
  document: (values) => `/projects/${values.pid}`,
  lessons: () => RISKS_READINESS_HREF,
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
  // Ticket 15: a package planned from a sentence, while I read the sentence (/packages/new) and once it is
  // saved (/packages/pkg-...). A STEP reference is never "new" and never starts with "pkg-".
  if (first === "packages" && parts.length === 2 && second === "new") return page("packageNew", "packages");
  // Ticket 38: an implementing agency officer's Check my plan, and one upload's check. PLAN.md section 8 does not list
  // these routes; "check" and "uploads" join "new" as words a package's id never is.
  if (first === "packages" && parts.length === 2 && second === "check") return page("checkMyPlan", "packages");
  if (first === "packages" && parts.length === 3 && second === "uploads") return page("uploadCheck", "packages", { id: third });
  if (first === "packages" && parts.length === 2 && PLANNED_ID.test(second)) return page("plannedPackage", "packages", { id: second });
  if (first === "packages" && parts.length === 2) return page("package", "packages", { id: second });
  if (first === "lessons" && parts.length === 1) return page("lessons", "lessons");
  // Ticket 29: the lesson review queue and one item's review page, for lesson reviewers.
  if (first === "lessons" && second === "review" && parts.length === 2) return page("lessonsQueue", "lessons");
  if (first === "lessons" && second === "review" && parts.length === 3) return page("lessonReview", "lessons", { itemId: third });
  // Ticket 32: Passage reports and one passage's reports, for passage reviewers, and Judging and one query, for
  // query judges.
  if (first === "lessons" && second === "reports" && parts.length === 2) return page("lessonsReports", "lessons");
  if (first === "lessons" && second === "reports" && parts.length === 3) return page("passageReport", "lessons", { groupId: third });
  if (first === "lessons" && second === "judging" && parts.length === 2) return page("lessonsJudging", "lessons");
  if (first === "lessons" && second === "judging" && parts.length === 3) return page("judgingQuery", "lessons", { queryId: third });
  if (first === "drafts" && parts.length === 1) return page("drafts", "drafts");
  // Ticket 35: writing a draft (/drafts/new?kind=...), and a draft by its id. PLAN.md section 8 does not
  // list these two routes; "new" is never a draft's id.
  if (first === "drafts" && parts.length === 2 && second === "new") return page("draftNew", "drafts");
  if (first === "drafts" && parts.length === 2) return page("draft", "drafts", { id: second });
  if (first === "data" && parts.length === 1) return page("data", "data");
  if (first === "data" && parts.length === 2 && second === DATA_PAGES.dataSources) return page("dataSources", "data");
  if (first === "data" && parts.length === 2 && Object.hasOwn(RETIRED_DATA_PAGES, second)) {
    return { ...page("data", "data"), canonical: RETIRED_DATA_PAGES[second], retired: true };
  }
  if (first !== "projects") return page("notFound");
  if (parts.length === 1) return page("projects", "projects");
  // Ticket 37: Following, before a project's address, so "following" is never read as a malformed project ID.
  // PLAN.md section 8 does not list this route.
  if (parts.length === 2 && second === "following") return page("following", "projects");

  if (!PROJECT_ID.test(second)) return page("notAProject");
  const pid = second.toUpperCase();
  let match: Match;
  const tab = parts.length === 2 ? "summary" : parts.length === 3 && Object.hasOwn(TAB_PATH, third) ? third : undefined;
  if (tab) {
    match = { ...page("project", "projects", { pid, tab }), frame: `project:${pid}` };
    if (tab === "summary" && parts.length === 3) match.canonical = `/projects/${pid}`;
  } else if (third === "procurement" && rest.length <= 1) {
    const [version] = rest;
    if (version !== undefined && !isDay(version)) return page("notFound");
    // Ticket 100: the plan check belongs to Packages, where a plan check is started and listed, though its address stays
    // under its project; in a view with no Packages it belongs to Projects.
    match = { ...page("checkPlan", "packages", { pid, agencyId: fourth, ...(version ? { version } : {}) }), fallbackSection: "projects" };
  } else if (third === "packages" && fourth && rest.length === 0) match = page("activity", "projects", { pid, stepRef: fourth });
  else if (third === "documents" && fourth && rest.length === 0) match = page("document", "projects", { pid, doc: fourth });
  else return page("notFound");
  if (pid !== second && !match.canonical) match.canonical = ["", ...raw.slice(0, 1), pid, ...raw.slice(2)].join("/");
  return match;
}

// A copy template with its {name} slots filled, for the browser tab's title.
export function fill(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (slot, name: string) => values[name] ?? slot);
}
