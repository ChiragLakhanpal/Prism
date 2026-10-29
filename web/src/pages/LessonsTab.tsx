// The Lessons tab (ticket 39; the 39 design brief, sections 2 and 5), at /lessons, in the wireframe's order:
//
// - The opening sentence, the digest: what came in since your last visit, each count word opening the items it
//   counts, then the sources note, then a quiet line for lessons you cite that only gained evidence. It is the page's
//   finding (ticket 102; DESIGN.md section 1, principle 6); a first visit's sentence reports a state, so it takes lead.
// - Then the Task zones, in this order (ticket 102; DESIGN.md section 5, Lessons page), each a panel when it holds
//   lessons or a form and a row when it holds only its sentence:
// - "Changed where you used it": one version notice per lesson and cited version in your open drafts, each with
//   was and now and the choices for every row that cites it. Left out when you have none.
// - "New": the lessons added since your last visit, at most eight cards.
// - "Your reports": what your "Wrong passage" reports fixed, a sentence, so always a row.
// - "The library": four filters, a count line that compares like with like, and the cards. An empty library is a
//   row whose sentences say whose lessons these are and where they show up, and never repeat the digest.
//
// One request returns everything, so the page renders once; a filter or a page change asks for the library alone.
// The server counts, compares versions, decides each tier and writes each count's word; this page counts nothing.
// When that one request fails, its error alert sits in the page's alert slot, the h1 names the page and nothing else
// draws (the shell redesign plan, 8.5).
import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LessonCard } from "../components/LessonCard";
import { fillText } from "../components/LessonParts";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { PageAlert } from "../components/PageAlert";
import { Pagination } from "../components/Pagination";
import { ProjectId } from "../components/ProjectId";
import { SkeletonText } from "../components/Skeleton";
import { TaskZone, ZoneBlock } from "../components/TaskZone";
import { DefinitionWindow } from "../components/Term";
import { TextLink } from "../components/TextLink";
import { VersionNotice } from "../components/VersionNotice";
import { copy } from "../copy";
import { getJson } from "../lib/api";
import { cx } from "../lib/cx";
import { draftHref } from "../lib/drafts";
import { evidenceIn, visited as visitedStore } from "../lib/evidence";
import { useLoad } from "../lib/load";
import type { Digest, Feedback, Filters, LessonsPageAnswer, LibraryAnswer, PageSegment, Strengthened } from "../lib/lessonsPage";
import { draftTitle, FILTER_KEYS, libraryHref, pageQuery, showHref } from "../lib/lessonsPage";
import { QUEUE_HREF } from "../lib/lessons";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { RISKS_READINESS_HREF } from "../routes";
import { refreshLessonsMe, useLessonsMe } from "../lib/lessonsMe";
import { LessonsFrame, LibrarySkeleton } from "./LessonsPages";

const w = copy.lessonsPage;
const server = copy.lessons.server;

// ── The server's sentences ───────────────────────────────────────────────

// A count with the word the server chose, which opens its items when the server named a popover for it.
function CountWord({ segment, popover }: { segment: Extract<PageSegment, { number: number }>; popover?: (key: string, word: ReactNode) => ReactNode }) {
  if (segment.numeral) return <Num value={segment.number} options={{ compact: false }} />;
  const word = segment.word ? (
    <span data-num className="tabular-nums">
      {segment.word}
    </span>
  ) : (
    <Num count={segment.number} capital={segment.capital} />
  );
  return segment.popover && popover ? <>{popover(segment.popover, word)}</> : word;
}

export function PageSentence({ segments, popover }: { segments: PageSegment[]; popover?: (key: string, word: ReactNode) => ReactNode }) {
  return (
    <>
      {segments.map((segment, index) => (
        <Fragment key={index}>
          {"text" in segment ? (
            segment.text
          ) : "number" in segment ? (
            <CountWord segment={segment} popover={popover} />
          ) : "date" in segment ? (
            segment.date ? <Num date={segment.date} /> : null
          ) : (
            <TextLink href={segment.href}>{segment.link}</TextLink>
          )}
        </Fragment>
      ))}
    </>
  );
}

// A count word's window: a heading that names it, then the items it counts, as links (a non-modal dialog).
function CountWindow({ word, title, children }: { word: ReactNode; title: ReactNode; children: ReactNode }) {
  return (
    <DefinitionWindow label={word} title={title}>
      {children}
    </DefinitionWindow>
  );
}

function Items({ children }: { children: ReactNode }) {
  return <ul className="flex flex-col gap-2">{children}</ul>;
}

// ── The digest ───────────────────────────────────────────────────────────

function digestPopover(digest: Digest, lastVisit: string | null, isReviewer: boolean) {
  const since = lastVisit ? <Num date={lastVisit} /> : null;
  const items = digest.items;
  const p = w.popovers;
  return (key: string, word: ReactNode): ReactNode => {
    if (key === "reports") {
      return (
        <CountWindow word={word} title={<Fill template={p.reports} slots={{ date: since }} />}>
          <Items>
            {(items.reports ?? []).map((report) => (
              <li key={report.document_id}>
                <Fill
                  template={p.reportItem}
                  slots={{ doc: report.doc_type, project: report.project_name ?? "", pid: <ProjectId pid={report.pid} />, date: report.disclosed_on ? <Num date={report.disclosed_on} style="table" /> : "" }}
                />
              </li>
            ))}
          </Items>
        </CountWindow>
      );
    }
    if (key === "new" || key === "changed" || key === "retired") {
      const listed = items[key] ?? [];
      const title = key === "new" ? p.new : key === "changed" ? p.changed : p.retired;
      return (
        <CountWindow word={word} title={<Fill template={title} slots={{ date: since }} />}>
          <Items>
            {listed.map((lesson) => (
              <li key={lesson.lesson_id} className="flex flex-col gap-0.5">
                <TextLink href={key === "new" ? `#new-lesson-${lesson.lesson_id}` : showHref(lesson.lesson_id, key === "retired")}>{lesson.statement}</TextLink>
                {key !== "new" && (
                  <span className="text-caption text-ink-muted">
                    <Fill
                      template={
                        key === "retired"
                          ? lesson.state === "retired_wrong"
                            ? p.retiredWrong
                            : p.retiredOutdated
                          : lesson.change_kind === "merged"
                            ? p.changedMerged
                            : p.changedWording
                      }
                      slots={{ version: <Num value={lesson.version} />, date: <Num date={lesson.decided_on} style="table" /> }}
                    />
                  </span>
                )}
                {(lesson.exported_uses ?? []).map((use) => (
                  <span key={use.draft_id} className="text-caption text-ink-muted">
                    <Fill template={p.retiredExported} slots={{ title: <TextLink href={draftHref(use.draft_id)}>{draftTitle(use.kind, use.subject)}</TextLink>, version: <Num value={use.cites} /> }} />
                  </span>
                ))}
              </li>
            ))}
          </Items>
        </CountWindow>
      );
    }
    if (key === "proposed") {
      return (
        <CountWindow word={word} title={p.proposed}>
          <p>{p.proposedBody}</p>
          {isReviewer && (
            <p className="mt-2">
              <TextLink href={QUEUE_HREF}>{p.proposedLink}</TextLink>
            </p>
          )}
        </CountWindow>
      );
    }
    if (key === "total") {
      return (
        <CountWindow word={word} title={p.total}>
          <p>{p.totalBody}</p>
          <p className="mt-2">
            <TextLink href="#library">{p.totalLink}</TextLink>
          </p>
        </CountWindow>
      );
    }
    return word;
  };
}

function StrengthenedLine({ strengthened }: { strengthened: Strengthened }) {
  const [open, setOpen] = useState(false);
  const many = strengthened.count === 1 ? "one" : "many";
  return (
    <div className="mt-3 flex flex-col gap-2" data-strengthened={open ? "open" : "closed"}>
      <p className="max-w-prose text-small text-ink-muted">
        <PageSentence segments={strengthened.segments} />{" "}
      </p>
      <div>
        <Button variant="ghost" flush icon={ChevronDown} aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? w.strengthenedHide[many] : w.strengthenedShow[many]}
        </Button>
      </div>
      {open && (
        <ul className="flex flex-col gap-3">
          {strengthened.items.map((item) => (
            <li key={`${item.lesson_id}-${item.a}`} className="flex flex-col gap-1 text-small">
              <p className="font-semibold text-ink-heading">{item.statement}</p>
              <dl className="grid grid-cols-[4rem_1fr] gap-x-4 gap-y-1">
                <dt className="font-semibold text-ink-heading">{copy.notice.was}</dt>
                <dd className="text-ink">
                  <Fill template={w.rested} slots={{ quotes: <Num count={item.was.quotes ?? 0} />, reports: <Num count={item.was.reports ?? 0} /> }} />
                </dd>
                <dt className="font-semibold text-ink-heading">{copy.notice.now}</dt>
                <dd className="text-ink">
                  <Fill template={w.rests} slots={{ quotes: <Num count={item.now.quotes ?? 0} />, reports: <Num count={item.now.reports ?? 0} /> }} />
                  <span className="block text-caption text-ink-muted">
                    <Fill template={copy.notice.decidedNow} slots={{ b: <Num value={item.b} />, date: <Num date={item.decided_on} /> }} />
                  </span>
                </dd>
              </dl>
              {item.uses.map((use) => (
                <p key={use.draft_id}>
                  <Fill template={copy.notice.usedIn} slots={{ title: <TextLink href={draftHref(use.draft_id)}>{draftTitle(use.kind, use.subject)}</TextLink>, a: <Num value={use.cites} /> }} />
                </p>
              ))}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// The finding's style (DESIGN.md section 3): 28/36 Light, 24/32 below a 48rem window, at most 22.5em wide, about 45
// characters a line, in balanced lines.
const FINDING = "max-w-[22.5em] text-finding text-balance text-ink-heading";

// The digest leads the page (ticket 102): the finding, with each count word still opening the items it counts, or on a
// first visit the status sentence in lead (the shell redesign plan, 8.5), then its caption and the sources note.
function DigestBlock({ page, isReviewer }: { page: LessonsPageAnswer; isReviewer: boolean }) {
  const digest = page.digest!;
  const first = digest.kind === "first";
  return (
    <div data-digest={digest.kind}>
      <p
        id="lessons-digest"
        className={first ? "max-w-prose text-lead text-pretty text-ink" : FINDING}
        data-finding={first ? undefined : ""}
        data-status-lead={first ? "" : undefined}
      >
        <PageSentence segments={digest.segments} popover={digestPopover(digest, page.visit?.last_visit_on ?? null, isReviewer)} />
      </p>
      {first && <p className="mt-2 max-w-prose text-caption text-ink-muted">{w.firstCaption}</p>}
      {/* 24 px after a finding, 4 px between a status sentence's captions (DESIGN.md section 4, space roles). */}
      <p className={cx("max-w-prose text-caption text-ink-muted", first ? "mt-1" : "mt-6")}>{copy.lessons.sourcesNote}</p>
      {digest.strengthened && <StrengthenedLine strengthened={digest.strengthened} />}
    </div>
  );
}

// ── Your reports ─────────────────────────────────────────────────────────

// A sentence about your reports, never a list of them, so the zone is a row (DESIGN.md section 1, principle 7).
function Reports({ feedback }: { feedback: Feedback }) {
  const p = w.popovers;
  const popover = (key: string, word: ReactNode) => {
    const [title, body] = key === "marked" ? [p.marked, p.markedBody] : key === "fixed" ? [p.fixed, p.fixedBody] : [p.recited, p.recitedBody];
    return (
      <CountWindow word={word} title={title}>
        <p>{body}</p>
      </CountWindow>
    );
  };
  return (
    <TaskZone
      headingId="lessons-reports"
      name={w.reportsTitle}
      marks={{ "data-reports": feedback.never ? "never" : "sentence" }}
      summary={
        feedback.never || !feedback.segments ? (
          <p>{w.reportsNone}</p>
        ) : (
          <p data-feedback-line>
            <PageSentence segments={feedback.segments} popover={popover} />
          </p>
        )
      }
    />
  );
}

// ── The library ──────────────────────────────────────────────────────────

const ANY: Record<string, string> = { stage: w.filters.anyStage, method: w.filters.anyMethod, sector: w.filters.anySector };

function FilterBar({ library, onChange, busy }: { library: LibraryAnswer; onChange: (next: Filters) => void; busy: boolean }) {
  const chosen = library.filters;
  const set = FILTER_KEYS.some((key) => key !== "status" ? Boolean(chosen[key]) : Boolean(chosen.status && chosen.status !== "current"));
  const stageRef = useRef<HTMLSelectElement>(null);
  return (
    <fieldset className="@container/filters" aria-busy={busy || undefined} data-filter-bar>
      <legend className="clip-visually">{w.filters.legend}</legend>
      {/* One row of selects, each as wide as its words, and a stack below 30rem (ticket 102, critique round 1). */}
      <div className="flex flex-col gap-3 @min-[30rem]/filters:flex-row @min-[30rem]/filters:flex-wrap @min-[30rem]/filters:gap-4">
        {FILTER_KEYS.map((key) => {
          const options = key === "status"
            ? library.options.status.map((option) => ({ key: option.key, label: w.filters.statuses[option.key] ?? option.key }))
            : library.options[key];
          const value = key === "status" ? (chosen.status ?? "current") : (chosen[key] ?? "");
          const isSet = key === "status" ? value !== "current" : Boolean(value);
          return (
            <label key={key} className="flex flex-col gap-1">
              <span className="text-small font-bold text-ink-heading">{w.filters[key]}</span>
              <span className="relative">
                <select
                  ref={key === "stage" ? stageRef : undefined}
                  value={value}
                  aria-describedby={key === "method" && chosen.method ? "method-caption" : undefined}
                  data-filter={key}
                  onChange={(event) => onChange({ ...chosen, [key]: event.target.value || null })}
                  // No type step of its own, so the base rule draws it at 16 px and a phone never zooms into it
                  // (DESIGN.md section 4, Phone baseline; ticket 102).
                  className={cx(
                    "h-11 w-full appearance-none rounded-sm border border-line-strong pr-10 pl-3 text-ink hover:bg-tint-hover @min-[30rem]/filters:w-auto @min-[30rem]/filters:min-w-48",
                    isSet ? "bg-tint shadow-[inset_0_0_0_2px_var(--color-primary)]" : "bg-surface",
                  )}
                >
                  {key !== "status" && <option value="">{ANY[key]}</option>}
                  {options.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <ChevronDown aria-hidden="true" className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-muted" />
              </span>
            </label>
          );
        })}
      </div>
      {set && (
        <div className="mt-2">
          <Button
            variant="ghost"
            flush
            onClick={() => {
              onChange({ stage: null, method: null, sector: null, status: null });
              requestAnimationFrame(() => stageRef.current?.focus());
            }}
          >
            {w.filters.reset}
          </Button>
        </div>
      )}
      {chosen.method && (
        <p id="method-caption" className="mt-2 max-w-prose text-caption text-ink-muted">
          {w.filters.methodCaption}
        </p>
      )}
    </fieldset>
  );
}

function LibrarySection({ initial, search, isReviewerWaiting }: { initial: LibraryAnswer; search: string; isReviewerWaiting: boolean }) {
  const [library, setLibrary] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  // The query the list shows, and the one last asked for: the page's own answer serves the first, so only a later
  // change asks again, including a change back to the starting filters or to page 1.
  const shown = useRef(libraryQuery(search));
  const asked = useRef(shown.current);
  const countRef = useRef<HTMLParagraphElement>(null);
  const here = useStore(address);
  const seen = useStore(visitedStore);
  const query = libraryQuery(search);
  useEffect(() => {
    if (query === asked.current) return;
    asked.current = query;
    const controller = new AbortController();
    setBusy(true);
    getJson<LibraryAnswer>(`/api/lessons/library${query}`, { signal: controller.signal }).then(
      (found) => {
        // An answer that arrived after a newer change cut it short is for filters the reader already left.
        if (controller.signal.aborted) return;
        shown.current = query;
        setLibrary(found);
        setBusy(false);
        setFailed(false);
      },
      () => {
        if (controller.signal.aborted) return;
        asked.current = shown.current;
        setBusy(false);
        setFailed(true);
      },
    );
    return () => {
      // A request cut short, by a newer change or by StrictMode's second run, is asked again next time.
      if (asked.current !== shown.current) asked.current = shown.current;
      controller.abort();
      setBusy(false);
    };
  }, [query]);
  const change = (next: Filters) => navigate(libraryHref(next), { replace: true, quiet: true });
  const noun = server.count.nouns[library.status][library.of === 1 ? "one" : "many"];
  const open = evidenceIn(here.search);
  if (library.of === 0 && library.status === "current" && !library.narrowed) {
    // The library holds no lesson yet, so its zone is a row (ticket 102) with no title of its own, since the digest
    // above already says the library is empty. The purpose above says whose lessons these are, so its sentences say
    // who decides and where the lessons show up on a package's page, and it links where section 3's own empty state
    // does (ticket 114); a reviewer with lessons waiting is led to them instead.
    const link = isReviewerWaiting ? { href: QUEUE_HREF, text: copy.lessons.library.reviewerLink } : { href: RISKS_READINESS_HREF, text: copy.pages.lessons.link };
    return (
      <TaskZone
        headingId="library"
        name={w.libraryTitle}
        // The page's empty state, as a zone row (DESIGN.md section 5, Task zone, No content).
        marks={{ "data-library": "empty", "data-empty-state": "row" }}
        summary={
          <div className="flex flex-col gap-2" data-library-empty>
            <p>{copy.pages.lessons.emptyBody}</p>
            <p>{copy.pages.lessons.emptyMore}</p>
            <p>
              <TextLink href={link.href}>{link.text}</TextLink>
            </p>
          </div>
        }
      />
    );
  }
  return (
    <TaskZone panel headingId="library" name={w.libraryTitle} marks={{ "data-library": "ready" }}>
      <ZoneBlock>
      {library.unknown_filter && (
        <Alert state="info">
          {w.filters.unknown}
        </Alert>
      )}
      <FilterBar library={library} onChange={change} busy={busy} />
      {failed && (
        <Alert state="error" live="alert">
          {w.filters.failed}
        </Alert>
      )}
      <p ref={countRef} tabIndex={-1} role="status" className="text-caption text-ink-muted outline-none" data-lead data-numbers>
        {busy ? w.filters.updating : <PageSentence segments={library.count} />}
      </p>
      {library.lessons.length === 0 && library.total > 0 ? (
        // A page past the end: lessons match, but not on this page (brief 29's out-of-range card).
        <EmptyState
          level={3}
          title={fillText(copy.lessons.library.outOfRangeTitle, { page: library.page })}
          body={
            library.pages === 1 ? (
              copy.lessons.library.outOfRangeBodyOne
            ) : (
              <Fill template={copy.lessons.library.outOfRangeBody} slots={{ pages: <Num count={library.pages} /> }} />
            )
          }
          link={{ href: libraryHref(library.filters), text: copy.lessons.library.firstPage }}
        />
      ) : library.lessons.length === 0 ? (
        <EmptyState
          level={3}
          title={fillText(w.nothingMatches, { noun })}
          body={w.nothingMatchesBody}
          link={{ href: libraryHref({ status: library.status === "current" ? null : library.status }), text: w.filters.reset }}
        />
      ) : (
        <ul aria-label={copy.lessons.library.list} className="flex flex-col gap-4">
          {library.lessons.map((card) => (
            <li key={card.lesson_id}>
              <LessonCard
                card={card}
                level={3}
                canRecheck={library.can_recheck}
                reasonMax={library.limits.reason_max_chars}
                onRecheckSaved={refreshLessonsMe}
                open={open}
                visited={seen}
                focus={library.shown === card.lesson_id}
              />
            </li>
          ))}
        </ul>
      )}
      {library.pages > 1 && (
        <div className="mt-4">
          <Pagination page={library.page} pages={library.pages} href={(n) => libraryHref(library.filters, n)} />
        </div>
      )}
      </ZoneBlock>
    </TaskZone>
  );
}

function libraryQuery(search: string): string {
  const asked = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of [...FILTER_KEYS, "page", "show"]) {
    const value = asked.get(key);
    if (value) kept.set(key, value);
  }
  const query = kept.toString();
  return query ? `?${query}` : "";
}

// ── The page ─────────────────────────────────────────────────────────────

// While the page loads: the digest's lines in the finding's style, the sources note (static copy, so it is in place
// before the lessons load), and the library's zone with its real header over the cards' frames.
function PageSkeleton() {
  return (
    <div aria-busy="true" data-lessons-page="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {w.loading}
      </p>
      <SkeletonText className="max-w-[22.5em] text-finding" widths={["w-full", "w-full", "w-[70%]"]} />
      <p className="mt-6 max-w-prose text-caption text-ink-muted">{copy.lessons.sourcesNote}</p>
      <div className="mt-8 @md/page:mt-12">
        <TaskZone panel name={w.libraryTitle}>
          <ZoneBlock>
            <LibrarySkeleton />
          </ZoneBlock>
        </TaskZone>
      </div>
    </div>
  );
}

export function LessonsBody({ page, search, isReviewer, isReviewerWaiting = false }: { page: LessonsPageAnswer; search: string; isReviewer: boolean; isReviewerWaiting?: boolean }) {
  return (
    <div data-lessons-page="ready" className="flex flex-col">
      {page.as_of ? (
        // The alert slot already says the page is as of a date, so this sentence reports the library's state as a
        // status line, not a second alert (DESIGN.md section 1, principle 6).
        <p className="max-w-prose text-lead text-pretty text-ink" data-status-lead>
          <Fill template={w.asOfNote} slots={{ date: <Num date={page.as_of} /> }} />
        </p>
      ) : (
        <>
          {page.digest && <DigestBlock page={page} isReviewer={isReviewer} />}
          {page.view === "preview" && <p className="mt-4 max-w-prose text-small text-ink-muted">{w.previewNote}</p>}
        </>
      )}
      {/* The zones, in the order the page reads (DESIGN.md section 5, Lessons page). */}
      <div data-zones className="mt-8 @md/page:mt-12">
        {page.notices.length > 0 && (
          <TaskZone panel headingId="lessons-changed" name={w.changedTitle} marks={{ "data-changed": "" }}>
            <ZoneBlock>
              {/* With nothing new, the digest says no lesson changed, so the zone says its changes came before then. */}
              <p className="max-w-prose text-caption text-ink-muted" data-zone-caption>
                {page.digest?.kind === "nothing" ? w.changedEarlierCaption(page.notices.length) : w.changedCaption}
              </p>
              <ul>
                {page.notices.map((notice) => (
                  <VersionNotice key={notice.anchor} notice={notice} />
                ))}
              </ul>
            </ZoneBlock>
          </TaskZone>
        )}
        {page.new_lessons && (
          <TaskZone panel headingId="lessons-new" name={w.newTitle} marks={{ "data-new": "" }}>
            <ZoneBlock>
              <p className="max-w-prose text-caption text-ink-muted">{w.newCaption}</p>
              <ul className="flex flex-col gap-4">
                {page.new_lessons.cards.map((card) => (
                  <li key={card.lesson_id} id={`new-lesson-${card.lesson_id}`}>
                    <LessonCard card={card} level={3} anchor={false} />
                  </li>
                ))}
              </ul>
              {page.new_lessons.more_segments && (
                <p className="max-w-prose text-caption text-ink-muted">
                  <PageSentence segments={page.new_lessons.more_segments} />
                </p>
              )}
            </ZoneBlock>
          </TaskZone>
        )}
        {page.feedback && <Reports feedback={page.feedback} />}
        <LibrarySection initial={page.library} search={search} isReviewerWaiting={isReviewerWaiting} />
      </div>
    </div>
  );
}

export function LessonsPage({ search }: { search: string }) {
  const me = useLessonsMe();
  // The page's own read keeps the address it opened with; a filter or a page change asks for the library alone.
  const [path] = useState(() => `/api/lessons/page${pageQuery(search)}`);
  const [load, retry] = useLoad<LessonsPageAnswer>(path);
  const isReviewer = me.status === "ready" && me.me.tabs.includes("review");
  const isReviewerWaiting = isReviewer && me.status === "ready" && (me.me.waiting ?? 0) > 0;
  return (
    <LessonsFrame pageKey="lessons" failed={load.status === "error"}>
      {load.status === "loading" ? (
        <PageSkeleton />
      ) : load.status === "error" ? (
        // The page's one read failed: its error alert goes to the alert slot, and the frame draws only the h1.
        <PageAlert>
          <LoadError error={load.error} message={w.error} permission={w.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </PageAlert>
      ) : (
        <LessonsBody page={load.data} search={search} isReviewer={isReviewer} isReviewerWaiting={isReviewerWaiting} />
      )}
    </LessonsFrame>
  );
}
