// How Strata works (the 16 design brief, section 8; the 47 brief, section 8): eight sections, each a short caption in
// Strata's own voice, then the figure the deck at /present shows (web/src/figures), without the deck's logo corner,
// and its text version. It reads no data and has no numbers, so it renders with the route even when the warehouse is
// down, and nothing here links to /present. Its last section, "What I don't do" (ticket 24; the 24 brief, section
// 4.7), lists each refusal's lead with its why, from the same copy keys the answer panel renders, so the link under
// every refusal keeps its promise.
import { useCallback, useId, useRef, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "../../components/Button";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import { figureCopy } from "../../deck/copy";
import { Diagram, FigureText, HairlineFigure, useOverflow } from "../../figures/Figure";
import { FIGURES, PAGE_ORDER, SLOTS, type FigureId } from "../../figures/registry";
import { DATA_HREF, WHAT_I_DONT_DO } from "../../routes";

const words = copy.dataReadiness.howPage;

function FigureSection({ id }: { id: FigureId }) {
  const figure = FIGURES[id];
  const text = figureCopy[id];
  const width = figure.slot === "hairline" ? 0 : SLOTS[figure.slot].width;
  const frame = useRef<HTMLDivElement>(null);
  const over = useOverflow(frame, width);
  const [chosen, setChosen] = useState<boolean | null>(null);
  const [broken, setBroken] = useState(false);
  const onFail = useCallback(() => setBroken(true), []);
  const open = broken || (chosen ?? over);
  const listId = useId();
  const headingId = `how-${id}`;
  return (
    <section aria-labelledby={headingId} className="scroll-mt-6" data-how-section={id}>
      <h2 id={headingId} tabIndex={-1} className="scroll-mt-6 text-h2 text-ink-heading outline-none">
        {text.heading}
      </h2>
      <p className="mt-4 max-w-prose text-body text-ink">{text.caption}</p>
      {"caption2" in text && <p className="mt-4 max-w-prose text-body text-ink">{text.caption2}</p>}
      <figure className="mt-6" data-how-figure={id}>
        {broken ? (
          <p className="text-caption text-ink-muted">{words.failed}</p>
        ) : figure.slot === "hairline" ? (
          <div className="relative w-full max-w-120" style={{ aspectRatio: "5 / 4" }}>
            <HairlineFigure onFail={onFail} className="w-full" />
          </div>
        ) : (
          <div
            ref={frame}
            className="max-w-full overflow-x-auto"
            tabIndex={over ? 0 : undefined}
            role={over ? "region" : undefined}
            aria-label={over ? words.scrolls(text.title) : undefined}
            data-overflow={over ? "" : undefined}
          >
            <div style={{ width }}>
              <Diagram id={id} />
            </div>
          </div>
        )}
      </figure>
      <div className="mt-4">
        {!broken && (
          <Button
            variant="ghost"
            flush
            icon={open ? ChevronUp : ChevronDown}
            aria-expanded={open}
            aria-controls={listId}
            onClick={() => setChosen(!open)}
          >
            {open ? words.hideText : words.showText}
          </Button>
        )}
        <div id={listId} hidden={!open} className="mt-2 max-w-prose">
          <FigureText id={id} />
        </div>
      </div>
    </section>
  );
}

export function HowStrataWorks() {
  return (
    <div className="flex flex-col gap-12">
      <div className="flex max-w-prose flex-col gap-4">
        <p tabIndex={-1} data-lead className="text-body outline-none">
          {words.lead}
        </p>
        <p className="text-body">
          {words.next.before}
          <TextLink href={DATA_HREF.data}>{words.next.readiness}</TextLink>
          {words.next.middle}
          <TextLink href={DATA_HREF.dataSources}>{words.next.sources}</TextLink>
          {words.next.after}
        </p>
        <nav aria-label={words.index} className="mt-2">
          <p className="text-label text-ink-muted">{words.index}</p>
          <ul className="mt-2 gap-x-8 text-body md:columns-2" data-how-index>
            {PAGE_ORDER.map((id) => (
              <li key={id} className="py-1">
                <TextLink href={`#how-${id}`}>{figureCopy[id].heading}</TextLink>
              </li>
            ))}
            <li className="py-1">
              <TextLink href={`#${WHAT_I_DONT_DO.id}`}>{words.dontDo.heading}</TextLink>
            </li>
          </ul>
        </nav>
      </div>
      {PAGE_ORDER.map((id) => (
        <FigureSection key={id} id={id} />
      ))}
      <WhatIDontDo />
    </div>
  );
}

// The page's last section, which the design gallery also shows on its own.
export function WhatIDontDo() {
  return (
      <section aria-labelledby={WHAT_I_DONT_DO.id} className="max-w-prose">
        <h2 id={WHAT_I_DONT_DO.id} tabIndex={-1} className="scroll-mt-6 text-h2 text-ink-heading outline-none">
          {words.dontDo.heading}
        </h2>
        <p className="mt-2 text-body">{words.dontDo.intro}</p>
        <dl data-dont-do className="mt-4 flex flex-col gap-4">
          {Object.entries(copy.refusals).map(([key, refusal]) => (
            <div key={key}>
              <dt className="text-body font-semibold text-ink">{refusal.lead}</dt>
              <dd className="mt-1 text-body text-ink">{refusal.why}</dd>
            </div>
          ))}
        </dl>
      </section>
  );
}
