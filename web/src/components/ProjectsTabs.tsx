// The Projects sub-tabs (ticket 37; the 37 brief, section 9.1): Following and All projects, as route links in a
// named nav, shown only to World Bank staff. Following's count is the server's, once the list has loaded.
import { copy } from "../copy";
import { formatNumber } from "../lib/format";
import { FOLLOWING_HREF } from "../lib/following";
import { Tabs } from "./Tabs";

export function ProjectsTabs({ following, count }: { following: boolean; count: number | null }) {
  const words = copy.projectsTabs;
  return (
    <div className="mt-6" data-projects-tabs>
      <Tabs
        label={words.label}
        tabs={[
          { key: "following", label: words.following(count === null ? null : formatNumber(count)), href: FOLLOWING_HREF, current: following },
          { key: "all", label: words.all, href: "/projects", current: !following },
        ]}
      />
    </div>
  );
}
