// The sidebar's items (DESIGN.md section 5, Sidebar; ticket 92), in order: Home, then the sections of the view the
// server applied, then Data at the sidebar's foot. Each item is one route, once, and routes.ts names the section each
// page belongs to. Adding a section is one entry here, its word in copy.nav.tabs, its view in config/roles.toml and its
// pages in routes.ts.
import { BookOpen, Database, FilePenLine, FolderOpen, House, Package, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { FOLLOWING_HREF } from "../lib/following";
import { formatNumber } from "../lib/format";
import { QUEUE_HREF, type Me as LessonsMe } from "../lib/lessons";
import { JUDGING_HREF, REPORTS_HREF } from "../lib/retrieval";
import { DATA_HREF, type PageKey } from "../routes";

export type Section = keyof typeof copy.nav.tabs;

export type SectionItem = { key: Section; href: string; icon: LucideIcon };

// Data sits at the sidebar's foot; the others in this order above it. The order is the user's (ticket 110): a project
// holds its Procurement Plan, and the plan holds the packages, so Projects comes before Packages.
export const SECTIONS: SectionItem[] = [
  { key: "projects", href: "/projects", icon: FolderOpen },
  { key: "packages", href: "/packages", icon: Package },
  { key: "lessons", href: "/lessons", icon: BookOpen },
  { key: "drafts", href: "/drafts", icon: FilePenLine },
  { key: "data", href: "/data", icon: Database },
];

export const FOOT_SECTION: Section = "data";

export const HOME_ITEM = { href: "/", icon: House };

// A section's own page, shown as an indented item under the section while it is current (Following and All projects
// under Projects, the reviewer pages under Lessons, Data's pages under Data). The tab tickets fill these; a page the
// applied view hides (config/roles.toml, GET /api/me's hidden) is left out. A sub-item may carry a count in a small
// badge, which is hidden at zero, with the words that say what it counts for a screen reader (ticket 102), and the
// path its own pages sit under, such as one item's review page under Waiting for review, where it keeps the mark.
export type SubItem = { pageKey: PageKey; label: string; href: string; count?: { text: string; words: string }; inside?: string };
export type SubItems = Partial<Record<Section, SubItem[]>>;

// The reviewer pages under Lessons each open for one role (GET /api/lessons/me's tabs), and count what waits there.
type LessonsRole = Exclude<LessonsMe["tabs"][number], "library">;
type LessonsCount = "waiting" | "reports_waiting" | "queries_left";

// The sub-items each section has, in order (ticket 99 fills Projects', ticket 104 Data's, ticket 102 Lessons'). A page
// for World Bank staff alone (staff) shows only to them in their own view, as Following does; a page for a Lessons role
// (role) only to the people who have it, with its count (count); the views' hidden pages (config/roles.toml) are left
// out by the sidebar. Adding a section's page is one entry here and its word in copy.nav.sub.
type SubEntry = {
  pageKey: keyof typeof copy.nav.sub & PageKey;
  href: string;
  staff?: boolean;
  role?: LessonsRole;
  count?: LessonsCount & keyof LessonsMe;
};
const SUB_ENTRIES: Partial<Record<Section, SubEntry[]>> = {
  projects: [
    { pageKey: "following", href: FOLLOWING_HREF, staff: true },
    { pageKey: "projects", href: "/projects" },
  ],
  lessons: [
    { pageKey: "lessonsQueue", href: QUEUE_HREF, role: "review", count: "waiting" },
    { pageKey: "lessonsReports", href: REPORTS_HREF, role: "reports", count: "reports_waiting" },
    { pageKey: "lessonsJudging", href: JUDGING_HREF, role: "judging", count: "queries_left" },
  ],
  data: [
    { pageKey: "data", href: DATA_HREF.data },
    { pageKey: "dataSources", href: DATA_HREF.dataSources },
  ],
};

const countWords = copy.nav.subCount as Partial<Record<PageKey, (count: string) => string>>;

// The sub-items for a viewer: staff is true for World Bank staff in their own view, never in a preview; lessons is the
// viewer's Lessons roles and counts (GET /api/lessons/me), or null until it answers, when no reviewer page shows.
export function subItemsFor(staff: boolean, lessons: LessonsMe | null = null): SubItems {
  const shown = (entry: SubEntry) => (staff || !entry.staff) && (!entry.role || Boolean(lessons?.tabs.includes(entry.role)));
  return Object.fromEntries(
    Object.entries(SUB_ENTRIES).map(([section, entries]) => [
      section,
      entries.filter(shown).map(({ pageKey, href, role, count }): SubItem => {
        const value = count && lessons ? (lessons[count] ?? 0) : 0;
        const words = countWords[pageKey];
        const text = formatNumber(value, { compact: false });
        return {
          pageKey,
          href,
          label: copy.nav.sub[pageKey],
          ...(value > 0 && words ? { count: { text, words: words(text) } } : {}),
          ...(role ? { inside: `${href}/` } : {}),
        };
      }),
    ]),
  );
}
