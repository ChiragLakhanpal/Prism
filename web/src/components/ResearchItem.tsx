// A deep research item in the evidence drawer (ticket 149): what a brief's marker opens, from the brief the page holds or
// from GET /api/evidence (ticket 148's reader of strata.research.item). Its fields in a two-column list (the outlet or
// agency, the date it was published or "Undated", the place, the day Prism read it), the source's own words as the
// reader kept them, never a summary Prism wrote, and "Open the source", the item's own page, in a new tab.
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { formatDate } from "../lib/format";
import type { ResearchItem } from "../lib/research";
import { ExternalLink } from "./ExternalLink";

export const RESEARCH_TABLE = "strata.research.item:";

export const isResearchItem = (evidence: EvidenceEvent | null | undefined): boolean =>
  Boolean(evidence && evidence.kind === "record" && evidence.id.startsWith(RESEARCH_TABLE));

export function ResearchItemView({ evidence }: { evidence: EvidenceEvent }) {
  const item = evidence.row as ResearchItem;
  const words = copy.research.item;
  const fields = [
    { label: words.source, value: item.author || item.source?.label },
    { label: words.published, value: item.date_known && item.published ? formatDate(item.published) : copy.research.undated },
    { label: words.place, value: item.location?.name ?? null },
    { label: words.readOn, value: item.read_on ? formatDate(item.read_on) : null },
  ].filter((field) => field.value);
  return (
    <div data-research-item data-passage-block className="flex flex-col gap-4 rounded-md border border-line p-4">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        {fields.map((field) => (
          <div key={field.label} className="min-w-0">
            <dt className="text-caption text-ink-muted">{field.label}</dt>
            <dd className="text-small wrap-break-word text-ink">{field.value}</dd>
          </div>
        ))}
      </dl>
      {item.text && (
        <div>
          <p className="text-caption text-ink-muted">{words.words}</p>
          <p className="mt-1 border-l-2 border-line-strong pl-3 text-small whitespace-pre-line text-ink">{item.text}</p>
        </div>
      )}
      {item.source?.license && <p className="text-caption text-ink-muted">{item.source.license}</p>}
      {typeof item.url === "string" && (
        <p>
          <ExternalLink href={item.url}>{copy.research.openSource}</ExternalLink>
        </p>
      )}
    </div>
  );
}
