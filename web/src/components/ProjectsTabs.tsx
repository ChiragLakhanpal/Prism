// The Projects sub-tabs (ticket 37; the 37 brief, sections 9.1 and 11.2): Following and All projects, as route links
// in a named nav, shown only to World Bank staff. The labels carry no count, so they read the same on both pages. A
// press opens the other page quietly: focus stays on the chosen sub-tab's link on the new page, and a polite status
// says which one opened, as a tab row inside one page keeps focus.
import { useEffect, useRef, useState } from "react";
import { copy } from "../copy";
import { FOLLOWING_HREF } from "../lib/following";
import { navigate } from "../lib/router";
import { createStore } from "../lib/store";
import { Tabs } from "./Tabs";

// The sub-tab just chosen, for the page it opens to give focus back to.
const chosen = createStore<string | null>(null);

export function ProjectsTabs({ following }: { following: boolean }) {
  const words = copy.projectsTabs;
  const row = useRef<HTMLDivElement>(null);
  const [said, setSaid] = useState("");
  useEffect(() => {
    const href = chosen.get();
    if (!href) return;
    chosen.set(null);
    row.current?.querySelector<HTMLElement>("a[aria-current=page]")?.focus();
    setSaid(words.announce(href === FOLLOWING_HREF ? words.following : words.all));
  }, []);
  return (
    <div className="mt-6" data-projects-tabs ref={row}>
      <Tabs
        label={words.label}
        tabs={[
          { key: "following", label: words.following, href: FOLLOWING_HREF, current: following },
          { key: "all", label: words.all, href: "/projects", current: !following },
        ]}
        onNavigate={(href) => {
          chosen.set(href);
          navigate(href, { quiet: true });
        }}
      />
      <p role="status" className="sr-only" data-subtab-status>
        {said}
      </p>
    </div>
  );
}
