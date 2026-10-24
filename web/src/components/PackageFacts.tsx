// The package workspace's header and facts (the 12 brief): the package's Description as the page's h1
// over its STEP reference, sticky from 768 px, and the package's facts as a definition list in STEP's
// field names, word for word, which are the defaults find_comparables started from. A missing value
// reads "Not in the plan row". "In the plan" links back to the plan check with this row in view.
import type { ReactNode, RefObject } from "react";
import { copy } from "../copy";
import type { PackageFacts } from "../lib/api";
import { formatNumber } from "../lib/format";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { SkeletonLine } from "./Skeleton";
import { TextLink } from "./TextLink";

const words = copy.packagePage;

export const mono = (text: string) => <span className="font-mono font-medium">{text}</span>;

export function PackageHeader({
  title,
  reference,
  headerRef,
  level = 1,
  sticky = true,
}: {
  title: ReactNode;
  reference: ReactNode;
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
      <p className="mt-1 text-small wrap-anywhere text-ink-muted">{reference}</p>
    </div>
  );
}

// The package's facts in STEP's field names, word for word: the defaults find_comparables started from.
export function PackageFactsList({ pkg }: { pkg: PackageFacts }) {
  const f = words.facts;
  const missing = <span className="text-ink-muted">{words.missing}</span>;
  const value = (text: string | null) => text ?? missing;
  const planHref = `/projects/${pkg.project_id}/procurement/${pkg.plan.agency_id}/${pkg.plan.plan_date}#${encodeURIComponent(pkg.step_reference)}`;
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

export function FactsSkeleton() {
  return (
    <div aria-hidden="true" className="grid grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-3">
      {Object.values(words.facts).map((label) => (
        <div key={label} className="flex flex-col">
          <span className="text-caption text-ink-muted">{label}</span>
          <SkeletonLine className="text-small" width="w-3/5" />
        </div>
      ))}
    </div>
  );
}
