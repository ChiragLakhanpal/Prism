// "Why this source" in the evidence drawer's passage view (ticket 22; the 22 brief, section 4; DESIGN.md section 5,
// Evidence drawer): why a paragraph is a source for a contract it appeared together with, in full sentences built
// from the link's score, part by part, so the words always match the score. It names the route's own activity on an
// activity page and the strongest link anywhere else, says what both concern and how far apart in time they are,
// says that a link means only that they appeared together, links to the contract's activity page, lists up to five
// other contracts, and keeps a closed "How I scored this link" table with each part's points, the total and the
// threshold, as the server rounded them. With no link public on the as-of date it shows nothing at all.
//
// A passage opened by its id carries the block in its own answer, asked for with the route's activity when the page
// has one (EvidenceDrawer's useEvidence), so no new URL parameter is needed.
import { useId, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { formatCount, formatDate } from "../lib/format";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { joinWords, topicWords, type Why } from "../lib/trail";
import { matchRoute } from "../routes";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { MonoWords } from "./MonoWords";
import { wholeDate } from "./NumFrom";
import { ProjectId } from "./ProjectId";
import { TextLink } from "./TextLink";

const words = copy.why;
const mono = (text: string) => <span className="font-mono">{text}</span>;
// A STEP reference in the sentence takes the scope chip's rule, so it moves to the next line whole rather than break
// after a hyphen, and its dates never break inside themselves (ticket 59; the critique of round 1, follow-up 1).
const reference = (text: string) => <MonoWords text={text} />;
const day = (iso: string) => wholeDate(formatDate(iso));

// The route's activity, when the page is an activity page: the contract "Why this source" names.
export function routeStepRef(pathname: string): string | null {
  const match = matchRoute(pathname);
  return match.key === "activity" ? (match.values.stepRef ?? null) : null;
}

// The block comes with the passage in the drawer's own read (GET /api/evidence), so it renders with it. A passage an
// answer's stream or a page sent with it carries no block (undefined) until the drawer asks for it (useEvidence).
export function useWhy(evidence: EvidenceEvent): Why | null {
  return evidence.why ?? null;
}

function timeSentence(why: Why) {
  const time = why.components.find((part) => part.part === "time");
  if (!time || Number(time.points) <= 0 || why.months === null || !why.document.date) return null;
  const slots = { doc: why.document.short_name ?? why.document.type, doc_date: day(why.document.date), months: String(why.months) };
  if (why.direction === "same" || why.months === 0) return <Fill template={words.timeSame} slots={slots} />;
  if (why.months === 1) return <Fill template={why.direction === "before" ? words.timeBeforeOne : words.timeAfterOne} slots={slots} />;
  return <Fill template={why.direction === "before" ? words.timeBefore : words.timeAfter} slots={slots} />;
}

function matched(why: Why, part: string, value: unknown) {
  const m = words.matched;
  if (part === "project") return <Fill template={m.project} slots={{ pid: <ProjectId pid={String(value)} /> }} />;
  if (part === "sector") return <Fill template={m.sector} slots={{ sector: String(value ?? "") }} />;
  if (part === "time") {
    if (value === null || value === undefined) return m.timeNone;
    if (value === 0) return m.timeSame;
    if (value === 1) return m.timeOne;
    return <Fill template={m.time} slots={{ months: String(value) }} />;
  }
  if (part === "text") {
    const terms = Array.isArray(value) ? (value as string[]) : [];
    return terms.length ? <Fill template={m.wording} slots={{ terms: terms.join(copy.list.comma) }} /> : m.wordingNone;
  }
  const mentions = Array.isArray(value) ? (value as string[]) : [];
  return mentions.length ? <Fill template={m.mentions} slots={{ mentions: joinWords(mentions, words.topicJoin) }} /> : m.mentionsNone;
}

export function WhyThisSource({ why }: { why: Why }) {
  const [open, setOpen] = useState(false);
  const tableId = useId();
  const headingId = useId();
  const topics = topicWords(why.topics);
  const state = words.projectState[why.project_state];
  const time = timeSentence(why);
  const ref = why.reference;
  // On the activity page it names, "Open the activity" would lead to the page you are on (design review F18).
  const here = useStore(address).pathname === why.activity_href;
  return (
    <section data-why aria-labelledby={headingId} className="flex flex-col gap-2">
      <h3 id={headingId} className="text-small font-bold text-ink-heading">
        {words.title}
      </h3>
      <p data-why-sentence className="max-w-prose text-small text-ink">
        <Fill
          template={words.link}
          slots={{ record_noun: words.recordNoun[why.record_noun] ?? why.record_noun, ref: reference(ref), signed_date: why.signed_on ? day(why.signed_on) : "" }}
        />{" "}
        {topics.length ? (
          <Fill template={words.topics} slots={{ topics: joinWords(topics, words.topicJoin), project_state: state }} />
        ) : (
          <Fill template={words.sameProject} slots={{ pid: <ProjectId pid={why.project_id} />, project_state: state }} />
        )}
        {time && <> {time}</>}
      </p>
      <p className="text-caption text-ink-muted">{words.only}</p>
      {why.activity_href && !here && (
        <p>
          <TextLink href={why.activity_href} className="inline-flex min-h-6 items-center text-small" data-why-activity>
            {words.open}
            <span className="clip-visually">{words.openFor(ref)}</span>
          </TextLink>
        </p>
      )}
      {why.others_count > 0 && (
        <div data-why-others>
          <p className="text-small text-ink">
            <Fill template={words.others(why.others_count)} slots={{ count: formatCount(why.others_count) }} />
          </p>
          <ul className="mt-1 flex flex-col gap-1">
            {why.others.map((other) => (
              <li key={other.reference} className="text-small">
                <Fill
                  template={words.othersItem}
                  slots={{
                    ref: other.href ? (
                      <TextLink href={other.href} className="inline-flex min-h-6 items-center font-mono">
                        {other.reference}
                      </TextLink>
                    ) : (
                      mono(other.reference)
                    ),
                    date: other.signed_on ? formatDate(other.signed_on, { style: "table" }) : "",
                  }}
                />
              </li>
            ))}
          </ul>
          {why.others_more > 0 && (
            <p className="mt-1 text-small">
              <TextLink href={why.connections_href} className="inline-flex min-h-6 items-center">
                <Fill template={words.othersMore(why.others_more)} slots={{ count: formatCount(why.others_more) }} />
              </TextLink>
            </p>
          )}
        </div>
      )}
      <div>
        <Button variant="ghost" flush icon={open ? ChevronUp : ChevronDown} aria-expanded={open} aria-controls={tableId} onClick={() => setOpen((shown) => !shown)}>
          {open ? words.scoreHide : words.scoreShow}
        </Button>
        <div id={tableId} hidden={!open}>
          <table data-why-score className="mt-2 w-full table-fixed text-small">
            <caption className="clip-visually">
              <Fill template={words.scoreCaption} slots={{ ref }} />
            </caption>
            <thead className="bg-surface-2 text-caption text-ink-muted">
              <tr>
                <th scope="col" className="w-1/4 px-2 py-2 text-left font-semibold">{words.col.part}</th>
                <th scope="col" className="px-2 py-2 text-left font-semibold">{words.col.matched}</th>
                <th scope="col" className="w-1/5 px-2 py-2 text-right font-semibold">{words.col.points}</th>
              </tr>
            </thead>
            <tbody>
              {why.components.map((part) => (
                <tr key={part.part} className="border-b border-line align-top">
                  <th scope="row" className="px-2 py-2 text-left font-semibold text-ink-heading">{words.part[part.part] ?? part.part}</th>
                  <td className="px-2 py-2 wrap-break-word text-ink">{matched(why, part.part, part.matched)}</td>
                  <td className="px-2 py-2 text-right tabular-nums">{part.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-small text-ink">
            <Fill template={words.total} slots={{ score: why.score, threshold: why.threshold }} />
          </p>
        </div>
      </div>
    </section>
  );
}
