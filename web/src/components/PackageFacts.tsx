// The package workspace's facts (the 12 brief; ticket 101; DESIGN.md section 5, Package header and facts): the side
// panel "From the plan row", in STEP's field names word for word, which are the defaults find_comparables started
// from: Method, Market Approach, Review Type, Estimated Amount (US$), Process Status and "In the plan", a link back to
// the plan check with this row in view. A missing value reads "Not in the plan row". Its source line names the plan
// version, and its marker opens the plan row in the evidence drawer. Below a frame of 75rem the panel is not drawn and
// the facts are one line in the page head (factsLine), with "Show the plan row", which opens the same record.
import { type ReactNode } from "react";
import { copy } from "../copy";
import type { PackageFacts } from "../lib/api";
import { formatNumber } from "../lib/format";
import { CitationMarker } from "./CitationMarker";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { planCheckHref } from "./PastRange";
import { ProjectId } from "./ProjectId";
import { SidePanel, type SideFact } from "./SidePanel";
import { Source } from "./Source";
import { TextLink } from "./TextLink";

const words = copy.packagePage;

export const mono = (text: string) => <span className="font-mono font-medium">{text}</span>;

// The package's facts in STEP's field names, word for word.
function factsOf(pkg: PackageFacts): SideFact[] {
  const f = words.facts;
  const missing = <span className="text-ink-muted">{words.missing}</span>;
  const value = (text: string | null) => text ?? missing;
  return [
    { label: f.method, value: value(pkg.method) },
    { label: f.marketApproach, value: value(pkg.market_approach) },
    { label: f.reviewType, value: value(pkg.review_type) },
    {
      label: f.estimated,
      // STEP's form with its cents, never shortened (DESIGN.md section 6).
      value: pkg.estimated_amount_usd ? (
        <span className="whitespace-nowrap tabular-nums">{formatNumber(Number(pkg.estimated_amount_usd), { decimals: 2, compact: false })}</span>
      ) : (
        missing
      ),
    },
    { label: f.processStatus, value: value(pkg.process_status), wide: true },
    {
      label: f.inPlan,
      wide: true,
      value: (
        <TextLink href={planCheckHref(pkg)}>
          <Fill
            template={words.inPlan}
            slots={{
              agency: pkg.plan.implementing_agency,
              // The date moves to the next line whole, as Num keeps a date in a sentence. An inline block takes no
              // underline from its link, so it inherits the link's own.
              date: (
                <span className="inline-block max-w-full [text-decoration:inherit] [&>[data-num]]:whitespace-normal">
                  <Num date={pkg.plan.plan_date} />
                </span>
              ),
            }}
          />
        </TextLink>
      ),
    },
  ];
}

// The facts' labels over value bars, while the package loads.
const LOADING_FACTS: SideFact[] = [
  { label: words.facts.method, value: null },
  { label: words.facts.marketApproach, value: null },
  { label: words.facts.reviewType, value: null },
  { label: words.facts.estimated, value: null },
  { label: words.facts.processStatus, value: null, wide: true },
  { label: words.facts.inPlan, value: null, wide: true },
];

// The side panel. opened: the drawer shows the plan row now; onOpen opens it from the marker.
export function FactsPanel({
  pkg,
  opened = false,
  onOpen,
}: {
  pkg: PackageFacts | null;
  opened?: boolean;
  onOpen?: (marker: HTMLElement) => void;
}) {
  if (!pkg) return <SidePanel title={words.factsTitle} facts={LOADING_FACTS} loading source={<span />} />;
  return (
    <div data-package-facts>
      <SidePanel
        title={words.factsTitle}
        facts={factsOf(pkg)}
        source={
          <Source>
            <Fill
              template={words.factsSource}
              slots={{
                agency: pkg.plan.implementing_agency,
                pid: <ProjectId pid={pkg.project_id} />,
                date: <Num date={pkg.plan.plan_date} />,
                page: String(pkg.plan.pdf_page),
              }}
            />
            <CitationMarker
              n={1}
              source={words.factsMarker(pkg.step_reference)}
              href={`?evidence=${encodeURIComponent(pkg.evidence_id)}`}
              drawerId="evidence-drawer"
              active={opened}
              onOpen={onOpen}
              evidenceId={pkg.evidence_id}
            />
          </Source>
        }
      />
    </div>
  );
}

// The facts in one line, for the page head below a frame of 75rem: "Request for Bids, Open - National, US$1,230,000,
// Pending Implementation", each value the plan row has.
export function factsLine(pkg: PackageFacts): ReactNode {
  const amount = pkg.estimated_amount_usd ? words.factsAmount(formatNumber(Number(pkg.estimated_amount_usd), { decimals: 0, compact: false })) : null;
  const parts = [pkg.method, pkg.market_approach, amount, pkg.process_status].filter((part): part is string => Boolean(part));
  return words.factsLine(parts);
}
