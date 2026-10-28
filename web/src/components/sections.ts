// The sidebar's items (DESIGN.md section 5, Sidebar; ticket 92), in order: Home, then the sections of the view the
// server applied, then Data at the sidebar's foot. Each item is one route, once, and routes.ts names the section each
// page belongs to. Adding a section is one entry here, its word in copy.nav.tabs, its view in config/roles.toml and its
// pages in routes.ts.
import { BookOpen, Database, FilePenLine, FolderOpen, House, Package, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { FOLLOWING_HREF } from "../lib/following";
import type { PageKey } from "../routes";

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
// applied view hides (config/roles.toml, GET /api/me's hidden) is left out.
export type SubItem = { pageKey: PageKey; label: string; href: string };
export type SubItems = Partial<Record<Section, SubItem[]>>;

// The sub-items each section has, in order (ticket 99 fills Projects'). A page for World Bank staff alone (staff) shows
// only to them in their own view, as Following does; the views' hidden pages (config/roles.toml) are left out by the
// sidebar. Adding a section's page is one entry here and its word in copy.nav.sub.
type SubEntry = { pageKey: keyof typeof copy.nav.sub & PageKey; href: string; staff?: boolean };
const SUB_ENTRIES: Partial<Record<Section, SubEntry[]>> = {
  projects: [
    { pageKey: "following", href: FOLLOWING_HREF, staff: true },
    { pageKey: "projects", href: "/projects" },
  ],
};

// The sub-items for a viewer: staff is true for World Bank staff in their own view, never in a preview.
export function subItemsFor(staff: boolean): SubItems {
  return Object.fromEntries(
    Object.entries(SUB_ENTRIES).map(([section, entries]) => [
      section,
      entries.filter((entry) => staff || !entry.staff).map(({ pageKey, href }) => ({ pageKey, href, label: copy.nav.sub[pageKey] })),
    ]),
  );
}
