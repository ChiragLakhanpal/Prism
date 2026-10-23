// Tabs on a light surface (DESIGN.md section 5): 16 px bold, five at most, the selected one
// with a 3 px primary underline. They are links in a nav with aria-current, because each one
// changes the address (the briefs for tickets 10 and 16 settled this). The navy bar's tabs
// are in TopNav, with a white underline.
import type { ReactNode } from "react";
import { cx } from "../lib/cx";

export type TabLink = { key: string; label: ReactNode; href: string; current?: boolean };

export function Tabs({ label, tabs }: { label: string; tabs: TabLink[] }) {
  return (
    <nav aria-label={label} className="border-b border-line">
      <ul className="flex flex-wrap gap-x-6">
        {tabs.slice(0, 5).map((tab) => (
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
