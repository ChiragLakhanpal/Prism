// The package workspace's header and facts (the 12 brief): the package's Description as the page's h1
// over its STEP reference, sticky from 768 px, and the package's facts as a definition list in STEP's
// field names, word for word, which are the defaults find_comparables started from. A missing value
// reads "Not in the plan row". "In the plan" links back to the plan check with this row in view.
import type { ReactNode, RefObject } from "react";
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
// A reference inside a sentence: with no spaces it is one box, so it moves to the next line whole when it
// fits there (DESIGN.md section 3, an ID stays readable as one ID), and wraps inside only when it is
// wider than the line, so the page never scrolls sideways; one with a county's name wraps at its spaces.
export const inlineMono = (text: string) => (
  <span className={cx("font-mono font-medium", !text.includes(" ") && "inline-block max-w-full wrap-anywhere")}>{text}</span>
);

export function PackageHeader({
  title,
  reference,
  headerRef,
  level = 1,
  sticky = true,
}: {
  title: ReactNode;
  // The STEP reference under the title, or null when the title is the reference itself.
  reference: ReactNode | null;
  headerRef?: RefObject<HTMLDivElement | null>;
  // The page's h1. The design gallery shows it one level down, under its own h1, and not sticky.
  level?: 1 | 2;
  sticky?: boolean;
}) {
  const Heading = level === 1 ? "h1" : "h2";
  return (
    <div ref={headerRef} data-package-header className={sticky ? "border-b border-line bg-page py-4 md:sticky md:top-0 md:z-10" : "border-b border-line bg-page py-4"}>
      <Heading tabIndex={-1} className="text-h1 text-pretty wrap-anywhere text-ink-heading focus:outline-none">
        {title}
      </Heading>
      {reference !== null && <p className="mt-1 text-small wrap-anywhere text-ink-muted">{reference}</p>}
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
        <Fill template={words.inPlan} slots={{ agency: pkg.plan.implementing_agency, date: <Num date={pkg.plan.plan_date} /> }} />
      </TextLink>,
    ],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-3" data-package-facts data-numbers>
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
// takes two lines from 768 px and three below, and Process Status two lines below 768 px.
const SKELETON_LINES: Partial<Record<keyof typeof words.facts, { narrow: number; wide: number }>> = {
  processStatus: { narrow: 2, wide: 1 },
  inPlan: { narrow: 3, wide: 2 },
};

export function FactsSkeleton() {
  const lines = (count: number) => Array.from({ length: count }, (_, index) => (index === count - 1 && count > 1 ? "w-3/5" : "w-4/5"));
  return (
    <div aria-hidden="true" className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-3">
      {(Object.entries(words.facts) as [keyof typeof words.facts, string][]).map(([key, label]) => {
        const held = SKELETON_LINES[key] ?? { narrow: 1, wide: 1 };
        return (
          <div key={label} className="flex flex-col">
            <span className="text-caption text-ink-muted">{label}</span>
            <SkeletonText className="text-small md:hidden" widths={lines(held.narrow)} />
            <SkeletonText className="hidden text-small md:flex" widths={lines(held.wide)} />
          </div>
        );
      })}
    </div>
  );
}
