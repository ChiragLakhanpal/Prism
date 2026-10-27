// The sidebar's items (DESIGN.md section 5, Sidebar; ticket 92), in order: Home, then the sections of the view the
// server applied, then Data at the sidebar's foot. Each item is one route, once, and routes.ts names the section each
// page belongs to. Adding a section is one entry here, its word in copy.nav.tabs, its view in config/roles.toml and its
// pages in routes.ts.
import { BookOpen, Database, FilePenLine, FolderOpen, House, Package, type LucideIcon } from "lucide-react";
import type { copy } from "../copy";
import type { PageKey } from "../routes";

export type Section = keyof typeof copy.nav.tabs;

export type SectionItem = { key: Section; href: string; icon: LucideIcon };

// Data sits at the sidebar's foot; the others in this order above it.
export const SECTIONS: SectionItem[] = [
  { key: "packages", href: "/packages", icon: Package },
  { key: "projects", href: "/projects", icon: FolderOpen },
  { key: "lessons", href: "/lessons", icon: BookOpen },
  { key: "drafts", href: "/drafts", icon: FilePenLine },
  { key: "data", href: "/data", icon: Database },
];

export const FOOT_SECTION: Section = "data";

export const HOME_ITEM = { href: "/", icon: House };

// A section's own page, shown as an indented item under the section while it is current (Following and All projects
// under Projects, the reviewer pages under Lessons, Data's pages under Data). The tab tickets fill these; a page the
// applied view hides (config/roles.toml, GET /api/me's hidden) is left out.
export type SubItem = { page: PageKey; label: string; href: string };
export type SubItems = Partial<Record<Section, SubItem[]>>;
