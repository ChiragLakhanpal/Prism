// The lesson card (DESIGN.md section 5; the 29 brief, sections 3.2 and 5.2): one lesson in the library, at its
// current version. Top to bottom: the kind and stage as an eyebrow, the statement as a heading, the lesson's
// first quote, a row of Source chips that open the evidence drawer, the evidence badge, the Tags (risk factors
// and sector, not controls), the decided line and the rules line, the source line, and for lesson reviewers
// only, "Ask for a re-check" with its inline form. It names roles, never people.
//
// The compact variant, under "This may repeat a lesson in the library" on a review page, keeps the eyebrow,
// the statement, the badge, the chips and "Version {version}, decided on {date}."
//
// More than six sources fold behind "Show {n} more sources". The re-check form opens under the button with
// no animation beyond a short fade, keeps its text when it closes, and Escape closes it.
import { createElement, Fragment, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import { ApiError, postJson } from "../lib/api";
import { cx } from "../lib/cx";
import type { LessonCard as Card, LessonEvidence } from "../lib/lessons";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { EvidenceBadge, fillText, SourceChip, Tag } from "./LessonParts";
import { ProjectId } from "./ProjectId";
import { Num } from "./Num";
import { ReasonField } from "./DecisionForm";
import { Source } from "./Source";
import { StatusBadge } from "./StatusBadge";

const words = copy.lessons;
const MOST_CHIPS = 6;

export function eyebrowOf(card: { kind: { label: string } | null; stage: { label: string } | null }): string {
  return fillText(words.card.eyebrow, { kind: card.kind?.label ?? "", stage: card.stage?.label ?? "" });
}

function Chips({ evidence, open, visited }: { evidence: LessonEvidence[]; open: string | null; visited: ReadonlySet<string> }) {
  const [all, setAll] = useState(false);
  const more = evidence.length - MOST_CHIPS;
  const shown = all || more <= 0 ? evidence : evidence.slice(0, MOST_CHIPS);
  return (
    <div className="flex flex-wrap items-center gap-2" data-source-chips>
      {shown.map((source) => (
        <SourceChip key={source.evidence_id} evidence={source} active={open === source.evidence_id} visited={visited.has(source.evidence_id)} />
      ))}
      {more > 0 && (
        <Button variant="ghost" aria-expanded={all} onClick={() => setAll(!all)}>
          {all ? words.card.fewerSources : more === 1 ? words.card.moreSource : fillText(words.card.moreSources, { count: more })}
        </Button>
      )}
    </div>
  );
}

// "Source: ICR, P130164, October 10, 2019, paragraph 54, page 23; ICR Review, ..."
export function LessonSources({ evidence, className }: { evidence: LessonEvidence[]; className?: string }) {
  return (
    <Source className={className}>
      {evidence.map((source, index) => (
        <Fragment key={source.evidence_id}>
          {index > 0 && words.card.sourceJoin}
          <Fill
            template={source.locator.kind === "section" ? words.card.sourceSection : words.card.sourceParagraph}
            slots={{
              doc: source.doc_short,
              pid: <ProjectId pid={source.pid} />,
              date: source.date ? <Num date={source.date} /> : "",
              para: source.locator.text,
              section: source.locator.text,
              page: String(source.page),
            }}
          />
        </Fragment>
      ))}
      {words.card.sourceEnd}
    </Source>
  );
}

type Recheck =
  | { state: "closed" }
  | { state: "open"; error: string | null }
  | { state: "saving" }
  | { state: "failed" }
  | { state: "saved"; on: string }
  | { state: "already"; on: string };

function RecheckForm({ card, max, onSaved }: { card: Card; max: number; onSaved: (on: string) => void }) {
  const [recheck, setRecheck] = useState<Recheck>({ state: "closed" });
  const [reason, setReason] = useState("");
  const [announced, setAnnounced] = useState("");
  const button = useRef<HTMLButtonElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const saved = useRef<HTMLParagraphElement>(null);
  const formId = useId();
  const open = recheck.state === "open" || recheck.state === "saving" || recheck.state === "failed";

  useEffect(() => {
    if (recheck.state === "open" && !recheck.error) field.current?.focus();
    if (recheck.state === "saved" || recheck.state === "already") saved.current?.focus();
  }, [recheck.state]);

  const close = () => {
    setRecheck({ state: "closed" });
    requestAnimationFrame(() => button.current?.focus());
  };

  const submit = async () => {
    if (!reason.trim()) {
      setRecheck({ state: "open", error: words.recheck.empty });
      field.current?.focus();
      return;
    }
    setRecheck({ state: "saving" });
    try {
      const done = await postJson<{ on: string; region: string }>(`/api/lessons/${encodeURIComponent(card.lesson_id)}/recheck`, { reason });
      setRecheck({ state: "saved", on: done.on });
      setAnnounced(fillText(words.recheck.announced, { region: done.region }));
      onSaved(done.on);
    } catch (error) {
      const refusal = error instanceof ApiError ? (error.body as { code?: string; values?: { on?: string } }) : null;
      if (refusal?.code === "recheck_open" && refusal.values?.on) setRecheck({ state: "already", on: refusal.values.on });
      else setRecheck({ state: "failed" });
    }
  };

  if (recheck.state === "saved" || recheck.state === "already") {
    return (
      <>
        <p ref={saved} tabIndex={-1} data-recheck={recheck.state} className="text-small text-ink outline-none">
          <Fill template={recheck.state === "saved" ? words.recheck.saved : words.recheck.open} slots={{ date: <Num date={recheck.on} /> }} />
        </p>
        <p role="status" className="clip-visually">
          {announced}
        </p>
      </>
    );
  }
  return (
    <div data-recheck={recheck.state}>
      {!open && (
        // Flush, so its label starts on the card's text edge like every other block (DESIGN.md section 5, Buttons).
        <Button ref={button} variant="ghost" flush aria-expanded={false} aria-controls={formId} onClick={() => setRecheck({ state: "open", error: null })}>
          {words.recheck.button}
        </Button>
      )}
      {open && (
        <form
          id={formId}
          noValidate
          aria-busy={recheck.state === "saving" || undefined}
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape" && recheck.state !== "saving") {
              event.stopPropagation();
              close();
            }
          }}
          className="flex animate-open-in flex-col gap-3 motion-reduce:animate-none"
        >
          {recheck.state === "failed" && (
            <Alert state="error" live="alert">
              {words.recheck.failed}
            </Alert>
          )}
          <ReasonField
            ref={field}
            label={words.recheck.label}
            helper={fillText(words.recheck.helper, { region: card.region ?? "" })}
            value={reason}
            onChange={setReason}
            max={max}
            error={recheck.state === "open" ? recheck.error : null}
            disabled={recheck.state === "saving"}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="submit" variant="secondary" loading={recheck.state === "saving"} busyLabel={words.recheck.saving}>
              {recheck.state === "failed" ? words.recheck.tryAgain : words.recheck.submit}
            </Button>
            <Button type="button" variant="ghost" disabled={recheck.state === "saving"} onClick={close}>
              {words.recheck.cancel}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

export function LessonCard({
  card,
  level = 2,
  compact = false,
  canRecheck = false,
  reasonMax,
  onRecheckSaved,
  open = null,
  visited = new Set(),
  children,
  focus = false,
  anchor = true,
}: {
  card: Card;
  level?: 2 | 3;
  compact?: boolean;
  canRecheck?: boolean;
  // The re-check reason's limit, which the library's answer gives from config/thresholds.toml.
  reasonMax?: number;
  // Called after a re-check is saved, so the sub-tab's count is asked for again.
  onRecheckSaved?: () => void;
  // The source the evidence drawer shows now, and the sources this viewer opened.
  open?: string | null;
  visited?: ReadonlySet<string>;
  // The lesson review writer's sentences about this lesson, under "This may repeat a lesson".
  children?: ReactNode;
  // Ticket 39: the card the library's ?show= opened, whose heading takes focus; and whether the card carries the
  // lesson's anchor, which "New" leaves to the library's card so the page holds one.
  focus?: boolean;
  anchor?: boolean;
}) {
  const headingId = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  const [rechecking, setRechecking] = useState(card.rechecking_since);
  const retired = card.retired ?? null;
  useEffect(() => {
    if (focus) heading.current?.focus();
  }, [focus]);
  return (
    <article
      id={compact || !anchor ? undefined : `lesson-${card.lesson_id}`}
      aria-labelledby={headingId}
      data-lesson-card={compact ? "compact" : "full"}
      data-retired={retired?.as}
      className={cx("flex flex-col gap-3 rounded-md border border-line bg-surface p-4 @md/page:p-6", compact && "@md/page:p-4")}
    >
      <p className="text-label text-ink-muted uppercase">{eyebrowOf(card)}</p>
      {createElement(
        `h${level}`,
        { id: headingId, ref: heading, tabIndex: focus ? -1 : undefined, className: "-mt-1 text-title text-balance text-ink-heading outline-none" },
        card.statement,
      )}
      {children}
      {!compact && card.quote && <p className="max-w-prose text-body text-ink">{fillText(words.card.quote, { quote: card.quote })}</p>}
      <Chips evidence={card.evidence} open={open} visited={visited} />
      <div className="flex flex-wrap gap-2">
        {retired && <StatusBadge kind={retired.as === "retired_wrong" ? "retired-wrong" : "retired-outdated"} />}
        <EvidenceBadge status={card.ieg_status} />
        {rechecking && <StatusBadge kind="rechecking" />}
      </div>
      {!compact && (
        <ul className="flex flex-wrap gap-2" aria-label={words.card.tags}>
          {[...(card.categories ?? []), ...(card.methods ?? [])].map((tag) => (
            <li key={tag.key}>
              <Tag>{tag.label}</Tag>
            </li>
          ))}
          {card.risk_factors.map((factor) => (
            <li key={factor.key}>
              <Tag>{factor.label}</Tag>
            </li>
          ))}
          {card.sector && (
            <li>
              <Tag>{card.sector}</Tag>
            </li>
          )}
        </ul>
      )}
      <div className="flex max-w-prose flex-col gap-1 text-caption text-ink-muted">
        {compact ? (
          <p>
            <Fill template={words.card.compactDecided} slots={{ version: <Num value={card.version} />, date: <Num date={card.decided_on} /> }} />
          </p>
        ) : (
          <>
            <p>
              <Fill template={words.card.decided} slots={{ version: <Num value={card.version} />, date: <Num date={card.decided_on} /> }} />
            </p>
            {rechecking && (
              <p>
                <Fill template={words.card.rechecking} slots={{ date: <Num date={rechecking} /> }} />
              </p>
            )}
            <p>{card.edition ? fillText(words.card.rules, { edition: card.edition.name }) : words.card.rulesUnknown}</p>
            {retired && (
              <p data-retired-line>
                <Fill template={copy.lessonsPage.retiredLine} slots={{ date: <Num date={retired.on} />, reason: retired.reason }} />
              </p>
            )}
          </>
        )}
      </div>
      {!compact && <LessonSources evidence={card.evidence} className="max-w-prose" />}
      {!compact && canRecheck && reasonMax !== undefined && !card.rechecking_since && !retired && (
        <RecheckForm
          card={card}
          max={reasonMax}
          onSaved={(on) => {
            setRechecking(on);
            onRecheckSaved?.();
          }}
        />
      )}
    </article>
  );
}
