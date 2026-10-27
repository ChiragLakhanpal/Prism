// The package workspace's header and facts (the 12 brief): the package's Description as the page's h1
// over its STEP reference, sticky from a page area of 768 px, and the package's facts as a definition list in STEP's
// field names, word for word, which are the defaults find_comparables started from. A missing value
// reads "Not in the plan row". "In the plan" links back to the plan check with this row in view.
import { type ReactNode, type RefObject } from "react";
import { copy } from "../copy";
import type { PackageFacts } from "../lib/api";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { planCheckHref } from "./PastRange";
import { SkeletonText } from "./Skeleton";
import { TextLink } from "./TextLink";

const words = copy.packagePage;

export const mono = (text: string) => <span className="font-mono font-medium">{text}</span>;

export function PackageHeader({
  title,
  reference,
  headerRef,
  level = 1,
  sticky = true,
  action,
}: {
  title: ReactNode;
  // The STEP reference under the title, or null when the title is the reference itself.
  reference: ReactNode | null;
  headerRef?: RefObject<HTMLDivElement | null>;
  // The page's h1. The design gallery shows it one level down, under its own h1, and not sticky.
  level?: 1 | 2;
  sticky?: boolean;
  // Ticket 36: "Suggest {n} PPSD risk rows" and its caption, at the header's right from 768 px.
  action?: ReactNode;
}) {
  const Heading = level === 1 ? "h1" : "h2";
  return (
    <div ref={headerRef} data-package-header className={sticky ? "border-b border-line bg-page py-4 @md/page:sticky @md/page:top-(--frame-top) @md/page:z-10" : "border-b border-line bg-page py-4"}>
      <div className="flex items-start justify-between gap-x-6">
        <div className="min-w-0 flex-1">
          <Heading tabIndex={-1} className="text-h1 text-pretty wrap-anywhere text-ink-heading focus:outline-none">
            {title}
          </Heading>
          {reference !== null && <p className="mt-1 text-small wrap-anywhere text-ink-muted">{reference}</p>}
        </div>
        {action}
      </div>
    </div>
  );
}

// The package's facts in STEP's field names, word for word: the defaults find_comparables started from.
export function PackageFactsList({ pkg }: { pkg: PackageFacts }) {
  const f = words.facts;
  const missing = <span className="text-ink-muted">{words.missing}</span>;
  const value = (text: string | null) => text ?? missing;
  const planHref = planCheckHref(pkg);
  const facts: [string, ReactNode][] = [
    [f.method, value(pkg.method)],
    [f.marketApproach, value(pkg.market_approach)],
    [f.reviewType, value(pkg.review_type)],
    [f.estimated, pkg.estimated_amount_usd ? formatNumber(Number(pkg.estimated_amount_usd), { decimals: 2, compact: false }) : missing],
    [f.processStatus, value(pkg.process_status)],
    [
      f.inPlan,
      <TextLink href={planHref}>
        <Fill
          template={words.inPlan}
          slots={{
            agency: pkg.plan.implementing_agency,
            // The date moves to the next line whole, as Num keeps a date in a sentence, and breaks at its
            // space only when it is wider than the column, as with WCAG 1.4.12's text spacing at 320 px.
            // An inline block takes no underline from its link, so it inherits the link's own.
            date: (
              <span className="inline-block max-w-full [text-decoration:inherit] [&>[data-num]]:whitespace-normal">
                <Num date={pkg.plan.plan_date} />
              </span>
            ),
          }}
        />
      </TextLink>,
    ],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 @md/page:grid-cols-3" data-package-facts data-numbers>
      {facts.map(([label, shown]) => (
        <div key={label} className="flex min-w-0 flex-col">
          <dt className="text-caption text-ink-muted">{label}</dt>
          <dd className="text-small wrap-break-word text-ink">{shown}</dd>
        </div>
      ))}
    </dl>
  );
}

// The facts' real labels over skeleton values. "In the plan" holds the agency's full name, which
// takes two lines from a page area of 768 px and three below, and Process Status two lines below it.
const SKELETON_LINES: Partial<Record<keyof typeof words.facts, { narrow: number; wide: number }>> = {
  processStatus: { narrow: 2, wide: 1 },
  inPlan: { narrow: 3, wide: 2 },
};

export function FactsSkeleton() {
  const lines = (count: number) => Array.from({ length: count }, (_, index) => (index === count - 1 && count > 1 ? "w-3/5" : "w-4/5"));
  return (
    <div aria-hidden="true" className="grid grid-cols-2 gap-x-6 gap-y-3 @md/page:grid-cols-3">
      {(Object.entries(words.facts) as [keyof typeof words.facts, string][]).map(([key, label]) => {
        const held = SKELETON_LINES[key] ?? { narrow: 1, wide: 1 };
        return (
          <div key={label} className="flex flex-col">
            <span className="text-caption text-ink-muted">{label}</span>
            <SkeletonText className="text-small @md/page:hidden" widths={lines(held.narrow)} />
            <SkeletonText className="hidden text-small @md/page:flex" widths={lines(held.wide)} />
          </div>
        );
      })}
    </div>
  );
}
