// Tabs on a light surface (DESIGN.md section 5): 16 px bold, five at most, the selected one
// with a 3 px primary underline. They are links in a nav with aria-current, because each one
// changes the address (the briefs for tickets 10 and 16 settled this). The navy bar's tabs
// are in TopNav, with a white underline.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

export type TabLink = { key: string; label: ReactNode; href: string; current?: boolean };

// DESIGN.md allows five tabs at most. A sixth is a mistake in the screen, so development
// builds stop on it rather than hide a tab; production shows every tab it is given.
export const MOST_TABS = 5;

export function Tabs({ label, tabs }: { label: string; tabs: TabLink[] }) {
  if (import.meta.env.DEV && tabs.length > MOST_TABS) {
    throw new Error(`Tabs got ${tabs.length} tabs, but DESIGN.md section 5 allows ${MOST_TABS} at most.`);
  }
  return (
    <nav aria-label={label} className="border-b border-line">
      <ul className="flex flex-wrap gap-x-6">
        {tabs.map((tab) => (
          <li key={tab.key}>
            <a
              href={tab.href}
              aria-current={tab.current ? "page" : undefined}
              className={cx(
                "relative flex h-11 items-center text-body font-bold transition-paint duration-150",
                "after:absolute after:inset-x-0 after:bottom-0 after:h-[3px] after:transition-paint after:duration-150",
                tab.current
                  ? "text-ink-heading after:bg-primary"
                  : "text-ink-muted hover:text-ink-heading hover:after:bg-line-strong",
              )}
            >
              {tab.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
