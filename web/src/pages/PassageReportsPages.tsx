// Lessons > Passage reports (ticket 32; the 32 design brief, sections 2.4, 2.5, 5.3 and 5.4), for passage reviewers:
//
// - /lessons/reports: the tab's purpose, the lead sentence, the caption that says ranking lower never hides a
//   paragraph, the groups waiting for you and for another reviewer (brief 29's Queue row), oldest first, and the
//   decisions of the last decided_days days in a table with Pagination.
// - /lessons/reports/:groupId: one passage's reports: the passage whole, what people reported (each sender by role,
//   never by name), and the Decision form, "Rank it lower" or "Keep its ranking" with a required reason; on an
//   audit sample, "Leave it ranked lower" or "Restore its ranking". A decided record shows its Outcome panel and
//   can be reopened with a reason.
//
// The server decides every act (src/strata/server/feedback.py); the page sends the state the reviewer saw, so an act
// on a group that moved on is refused as stale and nothing typed is lost. Both pages keep to the Lessons column.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { ReasonField } from "../components/DecisionForm";
import { PassageBlock } from "../components/EvidenceDrawer";
import { Fill } from "../components/Fill";
import { fillText } from "../components/LessonParts";
import { OutcomePanel } from "../components/LessonReview";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { Pagination } from "../components/Pagination";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { Table, type Row as TableRow } from "../components/Table";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { ApiError, postJson } from "../lib/api";
import { useLoad, type Load } from "../lib/load";
import { LESSONS_HREF, pageHref } from "../lib/lessons";
import {
  REPORTS_HREF,
  reportHref,
  type GroupRow,
  type PassageFields,
  type ReportGroup,
  type ReportsQueue,
  type SentReport,
} from "../lib/retrieval";
import { setPageTitle } from "../lib/title";
import { DocumentColumn } from "./DraftPage";
import { LessonsFrame, refreshLessonsMe, useMe } from "./LessonsPages";

const w = copy.passageReports;
const kindOf = (key: string) => copy.retrieval.queryKinds[key] ?? copy.retrieval.queryKinds.other;
const SHOWN = 5; // reports shown before "Show {n} more reports"

// A count in words from one to nine, as the copy file's number words give them.
const countWord = (count: number) => <Num count={count} />;

export function passageTitle(fields: Pick<PassageFields, "project_name" | "para" | "paragraph_numbered" | "section">): string {
  const project = fields.project_name ?? "";
  return fields.paragraph_numbered && fields.para
    ? fillText(w.rowTitle, { project, para: fields.para })
    : fillText(w.rowTitleSection, { project, section: fields.section ?? "" });
}

export function passageEvidence(passage: PassageFields & { row: Record<string, any> | null }): EvidenceEvent {
  return { id: passage.evidence_id, kind: "passage", tool: null, stratum: "Why", short_name: null, row: passage.row ?? {}, highlights: [] };
}

// ── The queue ────────────────────────────────────────────────────────────

export function GroupRowItem({ row }: { row: GroupRow }) {
  const kind = w.kindLabel[row.kind_label];
  return (
    <li data-report-row={row.group_id} className="flex flex-col gap-1 border-t-2 border-line py-4">
      <p className="text-small font-semibold text-ink-heading">{fillText(row.group === "you" ? w.status.you : w.status.others, { kind })}</p>
      <h3 className="text-title text-balance">
        <TextLink href={reportHref(row.group_id)}>{passageTitle(row)}</TextLink>
      </h3>
      <p className="text-caption text-ink-muted">
        <Fill
          template={w.rowSource}
          slots={{ docType: row.doc_type ?? "", date: row.doc_date ? <Num date={row.doc_date} /> : "", page: <Num value={row.page ?? 0} options={{ compact: false }} />, kind: kindOf(row.query_kind) }}
        />
      </p>
      {(row.own_project || row.audit) && (
        <div className="flex flex-wrap gap-2 py-1">
          {row.own_project && <StatusBadge kind="own-project" />}
          {row.audit && <StatusBadge kind="audit-sample" />}
        </div>
      )}
      <p className="text-small text-ink">
        {row.audit && row.decided_on ? (
          <Fill template={w.rowAudit} slots={{ date: <Num date={row.decided_on} />, agreeing: countWord(row.agreeing ?? 0) }} />
        ) : row.report_count === 1 ? (
          <Fill template={w.rowCountOne} slots={{ date: row.first_on ? <Num date={row.first_on} /> : "" }} />
        ) : (
          <Fill template={w.rowCount} slots={{ count: <Num count={row.report_count} capital />, date: row.first_on ? <Num date={row.first_on} /> : "" }} />
        )}
      </p>
      {row.group === "others" && row.reason_code && w.whyNot[row.reason_code] && <p className="text-small text-ink">{w.whyNot[row.reason_code]}</p>}
    </li>
  );
}

function Lead({ queue }: { queue: ReportsQueue }) {
  const { you, others, oldest_on: oldest } = queue.lead;
  const form = (forms: { one: string; many: string }, count: number) => (count === 1 ? forms.one : forms.many);
  const slots = {
    you: <Num count={you} />,
    others: <Num count={others} />,
    passagesYou: form(w.lead.passages, you),
    passagesOthers: form(w.lead.passages, others),
    beOthers: form(w.lead.be, others),
  };
  const template = you && others ? w.lead.both : you ? w.lead.youOnly : others ? w.lead.othersOnly : w.lead.none;
  return (
    <p tabIndex={-1} data-lead className="text-title text-ink-heading outline-none @md/page:text-h3" data-reports-lead>
      <Fill template={template} slots={slots} />
      {oldest && (you || others) ? (
        <>
          {" "}
          <Fill template={w.lead.oldest} slots={{ date: <Num date={oldest} /> }} />
        </>
      ) : null}
    </p>
  );
}

function Group({ groupKey, rows }: { groupKey: "you" | "others"; rows: GroupRow[] }) {
  if (rows.length === 0) return null;
  const id = `reports-${groupKey}`;
  return (
    <section aria-labelledby={id} data-report-group={groupKey}>
      <h2 id={id} className="text-title text-ink-heading">
        {w.groups[groupKey]}
      </h2>
      <p className="mt-1 text-caption text-ink-muted">{w.order}</p>
      <ul className="mt-4">
        {rows.map((row) => (
          <GroupRowItem key={row.group_id} row={row} />
        ))}
      </ul>
    </section>
  );
}

function Decided({ queue }: { queue: ReportsQueue }) {
  const decided = queue.decided;
  if (decided.total === 0) return null;
  const days = <Num value={decided.window_days} options={{ compact: false }} />;
  const rows: TableRow[] = decided.rows.map((row) => ({
    id: row.group_id,
    cells: {
      passage: (
        <span className="flex flex-col gap-0.5">
          <TextLink href={reportHref(row.group_id)}>{passageTitle(row)}</TextLink>
          <span className="text-caption text-ink-muted">{fillText(w.forQuestions, { kind: kindOf(row.query_kind) })}</span>
        </span>
      ),
      outcome: w.outcomes[row.outcome],
      decided: (
        <span className="whitespace-nowrap">
          <Num date={row.decided_on} style="table" />
        </span>
      ),
      reports: <Num value={row.report_count} options={{ compact: false }} />,
    },
  }));
  return (
    <div data-reports-decided>
      <Table
        level={2}
        title={<Fill template={w.decidedTitle} slots={{ days }} />}
        count={{ noun: w.decidedNoun, one: w.decidedNounOne, total: decided.total, from: decided.from, to: decided.to }}
        rowHeader="passage"
        columns={[
          { key: "passage", header: w.columns.passage, width: "w-[46%]" },
          { key: "outcome", header: w.columns.outcome, width: "w-[22%]", short: true },
          { key: "decided", header: w.columns.decided, width: "w-[18%]", short: true },
          { key: "reports", header: w.columns.reports, numeric: true, width: "w-[14%]" },
        ]}
        state={{ status: "ready", rows }}
        source={w.source}
      />
      {decided.pages > 1 && (
        <div className="mt-6">
          <Pagination page={decided.page} pages={decided.pages} href={(n) => pageHref(REPORTS_HREF, n)} />
        </div>
      )}
    </div>
  );
}

function Purpose({ queue }: { queue?: ReportsQueue | null }) {
  return (
    <p className="max-w-prose text-body text-ink-muted" data-reports-purpose>
      {queue?.mode === "scale" ? (
        <Fill template={w.purposeScale} slots={{ min: <Num count={queue.silver_min} />, every: <Num value={queue.audit_every} options={{ compact: false }} /> }} />
      ) : (
        w.purposePilot
      )}
    </p>
  );
}

export function ReportsBody({ queue }: { queue: ReportsQueue }) {
  const empty = queue.groups.you.length + queue.groups.others.length === 0;
  if (empty && queue.decided.total === 0) {
    return (
      <div className="flex flex-col gap-6" data-reports="empty">
        <Purpose queue={queue} />
        <EmptyState title={w.emptyTitle} body={w.emptyBody} />
      </div>
    );
  }
  return (
    <div data-reports="ready" className="flex flex-col">
      <Purpose queue={queue} />
      <div className="mt-6">
        <Lead queue={queue} />
      </div>
      <p className="mt-2 max-w-prose text-caption text-ink-muted">{w.caption}</p>
      {!empty && (
        <div className="mt-8 flex flex-col gap-8 @md/page:mt-12 @md/page:gap-12">
          <Group groupKey="you" rows={queue.groups.you} />
          <Group groupKey="others" rows={queue.groups.others} />
        </div>
      )}
      <div className="mt-8 @md/page:mt-12">
        <Decided queue={queue} />
      </div>
    </div>
  );
}

export function ReportsSkeleton() {
  return (
    <div aria-busy="true" data-reports="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {w.loading}
      </p>
      <Purpose />
      <span className="mt-6 flex flex-col text-title @md/page:text-h3">
        <SkeletonLine width="w-[70%]" />
      </span>
      <SkeletonLine className="mt-2 text-caption" width="w-1/2" />
      <div className="mt-8 @md/page:mt-12">
        {[0, 1, 2].map((index) => (
          <div key={index} className="flex flex-col gap-1 border-t-2 border-line py-4" data-skeleton-row>
            <SkeletonLine className="text-small" width="w-[30%]" />
            <SkeletonLine className="text-title" width="w-[60%]" />
            <SkeletonLine className="text-caption" width="w-[80%]" />
            <SkeletonLine className="text-small" width="w-[40%]" />
          </div>
        ))}
      </div>
    </div>
  );
}

function NoAccess() {
  return <EmptyState title={w.noAccessTitle} body={w.noAccessBody} link={{ href: LESSONS_HREF, text: w.noAccessLink }} />;
}

const refusedAs = (load: Load<unknown>, code: string) =>
  load.status === "error" && (load.error?.body as { code?: string } | undefined)?.code === code;

function pageOf(search: string): number {
  const asked = Number(new URLSearchParams(search).get("page") ?? "1");
  return Number.isInteger(asked) && asked >= 1 ? asked : 1;
}

export function ReportsView({ load, retry }: { load: Load<ReportsQueue>; retry: () => void }) {
  if (load.status === "loading") return <ReportsSkeleton />;
  if (load.status === "error") {
    if (refusedAs(load, "not_a_passage_reviewer")) return <NoAccess />;
    return <LoadError error={load.error} message={w.error} permission={w.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />;
  }
  return <ReportsBody queue={load.data} />;
}

export function PassageReportsPage({ search }: { search: string }) {
  const me = useMe();
  const [load, retry] = useLoad<ReportsQueue>(`/api/passage-reports?page=${pageOf(search)}`);
  const denied = refusedAs(load, "not_a_passage_reviewer");
  useEffect(() => {
    if (denied) setPageTitle(copy.pages.lessons.title);
  }, [denied]);
  return (
    <LessonsFrame tabKey="reports" me={me}>
      <ReportsView load={load} retry={retry} />
    </LessonsFrame>
  );
}

// ── One passage's reports ────────────────────────────────────────────────

function roleSentence(report: SentReport): string {
  return copy.retrieval.roles[report.is_you ? "you" : report.role] ?? copy.retrieval.roles.staff;
}

export function ReportItem({ report }: { report: SentReport }) {
  const you = report.is_you;
  return (
    <li data-report-item={report.report_id} className="flex flex-col gap-1 border-t border-line py-4 first:border-t-0 first:pt-0">
      <p className="text-small font-semibold text-ink">
        <Fill template={w.reportFirst[report.kind]} slots={{ role: roleSentence(report), date: <Num date={report.reported_on} /> }} />
      </p>
      {report.own_project && (
        <div className="py-1">
          <StatusBadge kind="their-project" />
        </div>
      )}
      <p className="text-small text-ink">{fillText(you ? w.askedYou : w.asked, { question: report.question })}</p>
      {report.sentence && <p className="text-small text-ink">{fillText(w.sentence, { sentence: report.sentence })}</p>}
      <p className="text-small text-ink">
        {report.reason ? fillText(you ? w.reasonYou : w.reason, { reason: report.reason }) : you ? w.noReasonYou : w.noReason}
      </p>
      <p className="text-caption text-ink-muted">
        <Fill template={w.answerId} slots={{ id: <span className="font-mono wrap-anywhere">{report.run_id}</span> }} />
      </p>
    </li>
  );
}

function Reports({ group }: { group: ReportGroup }) {
  const [all, setAll] = useState(false);
  const id = useId();
  const shown = all ? group.reports : group.reports.slice(0, SHOWN);
  const more = group.reports.length - SHOWN;
  return (
    <section aria-labelledby={id} className="mt-8 @md/page:mt-12">
      <h2 id={id} className="text-title text-ink-heading">
        {w.reportsTitle}
      </h2>
      <p className="mt-1 text-caption text-ink-muted">{w.reportsCaption}</p>
      <ol className="mt-4">
        {shown.map((report) => (
          <ReportItem key={report.report_id} report={report} />
        ))}
      </ol>
      {more > 0 && (
        <Button variant="ghost" flush onPage onClick={() => setAll(!all)} aria-expanded={all}>
          {all ? w.showFewer : fillText(w.showMore, { count: more })}
        </Button>
      )}
    </section>
  );
}

type Saved = { saved: { outcome: string; next: string | null }; item: ReportGroup };
type GaveWay = { kind: "stale"; name: string | null; time: string | null; reason: string } | { kind: "lost" };

function DecisionForm({ group, onSaved, onGaveWay, initial }: {
  group: ReportGroup;
  onSaved: (saved: Saved) => void;
  onGaveWay: (gaveWay: GaveWay, item?: ReportGroup) => void;
  initial?: { reason?: string; error?: boolean; failed?: boolean; saving?: string };
}) {
  const headingId = useId();
  const audit = group.stage === "audit";
  const [reason, setReason] = useState(initial?.reason ?? "");
  const [showError, setShowError] = useState(initial?.error ?? false);
  const [saving, setSaving] = useState<string | null>(initial?.saving ?? null);
  const [failed, setFailed] = useState(initial?.failed ?? false);
  const [last, setLast] = useState(audit ? "leave_lower" : "rank_lower");
  const field = useRef<HTMLTextAreaElement>(null);
  const buttons = audit
    ? [{ outcome: "leave_lower", label: w.form.leaveLower, variant: "primary" as const }, { outcome: "restore", label: w.form.restore, variant: "secondary" as const }]
    : [{ outcome: "rank_lower", label: w.form.rankLower, variant: "primary" as const }, { outcome: "keep", label: w.form.keep, variant: "secondary" as const }];

  async function send(outcome: string) {
    setLast(outcome);
    if (!reason.trim()) {
      setShowError(true);
      requestAnimationFrame(() => field.current?.focus());
      return;
    }
    setSaving(outcome);
    setFailed(false);
    try {
      onSaved(await postJson<Saved>(`/api/passage-reports/${encodeURIComponent(group.group_id)}/decide`, {
        expected_state: group.state, outcome, reason: reason.trim(),
      }));
    } catch (error) {
      setSaving(null);
      const body = error instanceof ApiError ? (error.body as { code?: string; values?: { name?: string; time?: string }; item?: ReportGroup }) : null;
      if (body?.code === "stale") onGaveWay({ kind: "stale", name: body.values?.name ?? null, time: body.values?.time ?? null, reason }, body.item);
      else if (body?.code === "not_a_passage_reviewer") onGaveWay({ kind: "lost" });
      else setFailed(true);
    }
  }

  return (
    <div data-report-decision={group.stage} className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <form noValidate aria-labelledby={headingId} aria-busy={saving !== null || undefined} onSubmit={(event) => event.preventDefault()} className="flex flex-col gap-4">
        <h2 id={headingId} className="text-title text-ink-heading">
          {w.form.title}
        </h2>
        {failed && (
          <Alert state="error" live="alert" action={<Button variant="secondary" onClick={() => void send(last)}>{w.form.tryAgain}</Button>}>
            {w.form.failed}
          </Alert>
        )}
        <ReasonField
          ref={field}
          label={w.form.reasonLabel}
          helper={w.form.reasonHelper}
          value={reason}
          onChange={setReason}
          max={group.limits.reason_max_chars}
          error={showError && !reason.trim() ? w.form.noReason : null}
          disabled={saving !== null}
        />
        <div className="flex flex-col gap-3 @md/page:flex-row @md/page:flex-wrap">
          {buttons.map((button) => (
            <Button
              key={button.outcome}
              variant={button.variant}
              loading={saving === button.outcome}
              busyLabel={w.form.saving}
              disabled={saving !== null && saving !== button.outcome}
              onClick={() => void send(button.outcome)}
              className="w-full @md/page:w-auto"
              data-outcome={button.outcome}
            >
              {button.label}
            </Button>
          ))}
        </div>
        <p className="max-w-prose text-caption text-ink-muted">{fillText(audit ? w.form.feedforwardAudit : w.form.feedforward, { kind: kindOf(group.query_kind) })}</p>
      </form>
    </div>
  );
}

function Record({ group, onReopened, initialOpen = false }: { group: ReportGroup; onReopened: (item: ReportGroup) => void; initialOpen?: boolean }) {
  const outcome = group.outcome!;
  const [open, setOpen] = useState(initialOpen);
  const [reason, setReason] = useState("");
  const [error, setError] = useState(false);
  const [saving, setSaving] = useState(false);
  const field = useRef<HTMLTextAreaElement>(null);
  const kind = kindOf(group.query_kind);
  const lead = (
    <Fill
      template={w.record[outcome.outcome]}
      slots={{ kind, date: <Num date={outcome.decided_on} />, name: outcome.reviewer_name ?? "", agreeing: countWord(outcome.agreeing ?? 0) }}
    />
  );
  const state = outcome.outcome === "ranked_lower" || outcome.outcome === "ranked_lower_by_agreement" || outcome.outcome === "left_lower" ? "success" : "neutral";
  useEffect(() => {
    if (open) field.current?.focus();
  }, [open]);

  async function reopen() {
    if (!reason.trim()) {
      setError(true);
      field.current?.focus();
      return;
    }
    setSaving(true);
    try {
      const found = await postJson<{ item: ReportGroup }>(`/api/passage-reports/${encodeURIComponent(group.group_id)}/reopen`, { reason: reason.trim() });
      onReopened(found.item);
    } catch {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4" data-report-record={outcome.outcome}>
      <OutcomePanel state={state} lead={lead} body={outcome.reason ? fillText(w.recordReason, { reason: outcome.reason }) : ""} />
      {!open ? (
        <div>
          <Button variant="ghost" flush onPage onClick={() => setOpen(true)} aria-expanded={false} data-reopen>
            {w.reopen}
          </Button>
        </div>
      ) : (
        <form
          noValidate
          onSubmit={(event) => event.preventDefault()}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              setOpen(false);
            }
          }}
          className="flex animate-fade-in flex-col gap-4 rounded-md border border-line bg-surface p-4 motion-reduce:animate-none @md/page:p-6"
        >
          <ReasonField ref={field} label={w.reopenLabel} helper={w.reopenHelper} value={reason} onChange={setReason} max={group.limits.reason_max_chars} error={error && !reason.trim() ? w.reopenNoReason : null} disabled={saving} />
          <div className="flex flex-col gap-3 @md/page:flex-row">
            <Button variant="secondary" loading={saving} busyLabel={w.form.saving} onClick={() => void reopen()} className="w-full @md/page:w-auto">
              {w.reopen}
            </Button>
            <Button variant="ghost" onClick={() => setOpen(false)} disabled={saving}>
              {copy.feedback.cancel}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

export function ReportGroupView({ group: loaded, initial, sample = false }: {
  group: ReportGroup;
  initial?: { saved?: Saved; gaveWay?: GaveWay; form?: Parameters<typeof DecisionForm>[0]["initial"]; reopenOpen?: boolean; reopened?: boolean };
  // A design gallery sample: its title is an h3, under the gallery page's own h1, and it names no browser tab.
  sample?: boolean;
}) {
  const Title = sample ? "h3" : "h1";
  const [group, setGroup] = useState(loaded);
  const [saved, setSaved] = useState<Saved | null>(initial?.saved ?? null);
  const [gaveWay, setGaveWay] = useState<GaveWay | null>(initial?.gaveWay ?? null);
  const [reopened, setReopened] = useState(initial?.reopened ?? false);
  const heading = useRef<HTMLHeadingElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const passageId = useId();
  const kind = kindOf(group.query_kind);
  const status = fillText(group.stage === "decided" ? w.status.decided : group.can.decide ? w.status.you : w.status.others, { kind: w.kindLabel[group.kind_label] });
  useEffect(() => setGroup(loaded), [loaded]);
  useEffect(() => {
    if (!sample && (document.activeElement === document.body || document.activeElement === null)) heading.current?.focus({ preventScroll: true });
  }, []);
  useEffect(() => {
    if (!sample) setPageTitle(fillText(w.pageTitle, { project: group.passage.project_name ?? "", para: group.passage.para ?? "" }));
  }, [group.passage.project_name, group.passage.para]);
  useEffect(() => {
    if (saved || reopened || gaveWay) panel.current?.focus();
  }, [saved, reopened, gaveWay]);

  let action: ReactNode = null;
  if (saved) {
    const words = w.saved[saved.saved.outcome];
    const next = saved.saved.next ? { href: reportHref(saved.saved.next), text: w.nextReport } : { href: REPORTS_HREF, text: w.backToReports };
    action = (
      <OutcomePanel
        ref={panel}
        state={saved.saved.outcome === "rank_lower" || saved.saved.outcome === "leave_lower" ? "success" : "neutral"}
        lead={fillText(words.lead, { kind })}
        body={words.body}
        links={[next]}
      />
    );
  } else if (reopened) {
    action = <OutcomePanel ref={panel} state="info" lead={w.reopenedLead} body={w.reopenedBody} />;
  } else if (gaveWay?.kind === "stale") {
    action = (
      <div ref={panel} tabIndex={-1} className="flex flex-col gap-4 outline-none" data-gave-way="stale">
        <Alert state="info" live="status">
          <Fill template={w.form.stale} slots={{ name: gaveWay.name ?? "", date: gaveWay.time ? <Num date={gaveWay.time} /> : "" }} /> {w.form.staleBody}
        </Alert>
        <ReasonField label={w.form.staleReason} value={gaveWay.reason} max={group.limits.reason_max_chars} readOnly />
      </div>
    );
  } else if (gaveWay?.kind === "lost") {
    action = (
      <div ref={panel} tabIndex={-1} className="outline-none" data-gave-way="lost">
        <Alert state="error" live="alert">
          {w.form.lostRole}
        </Alert>
      </div>
    );
  } else if (group.stage === "decided" && group.outcome) {
    action = <Record group={group} initialOpen={initial?.reopenOpen} onReopened={(item) => { setGroup(item); setReopened(true); void refreshLessonsMe(); }} />;
  } else if (group.can.decide) {
    action = (
      <DecisionForm
        group={group}
        initial={initial?.form}
        onSaved={(found) => {
          setGroup(found.item);
          setSaved(found);
          void refreshLessonsMe();
        }}
        onGaveWay={(found, item) => {
          if (item) setGroup(item);
          setGaveWay(found);
        }}
      />
    );
  } else if (group.can.reason_code === "own_report") {
    action = (
      <Alert state="neutral">
        {w.form.ownReport}
      </Alert>
    );
  }

  return (
    <div data-report-page={group.group_id} className="flex flex-col">
      <Breadcrumb held trail={[{ text: copy.lessons.tabs.library, href: LESSONS_HREF }, { text: w.title, href: REPORTS_HREF }, { text: w.kindLabel[group.kind_label] }]} back={{ text: w.breadcrumbBack, href: REPORTS_HREF }} />
      <p className="mt-4 text-small font-semibold text-ink-heading" data-status>
        {status}
      </p>
      <Title ref={heading} tabIndex={-1} className="mt-2 text-h1 text-balance wrap-anywhere text-ink-heading focus:outline-none">
        {passageTitle(group.passage)}
      </Title>
      <p className="mt-2 text-body text-ink-muted">
        {group.report_count === 1 ? (
          <Fill template={w.contextOne} slots={{ kind, date: group.first_on ? <Num date={group.first_on} /> : "" }} />
        ) : (
          <Fill template={w.context} slots={{ kind, count: <Num count={group.report_count} capital />, date: group.first_on ? <Num date={group.first_on} /> : "" }} />
        )}
      </p>
      {group.own_project && (
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge kind="own-project" />
        </div>
      )}
      {group.audit && (
        <div className="mt-3">
          <Alert state="info">
            <Fill template={w.auditContext} slots={{ date: <Num date={group.audit.decided_on} />, agreeing: countWord(group.audit.agreeing ?? 0) }} />
          </Alert>
        </div>
      )}
      <section aria-labelledby={passageId} className="mt-8 flex flex-col gap-4 @md/page:mt-12">
        <h2 id={passageId} className="text-title text-ink-heading">
          {w.passageTitle}
        </h2>
        <PassageBlock evidence={passageEvidence(group.passage)} />
      </section>
      {group.reports.length > 0 && <Reports group={group} />}
      {action && (
        <div className="mt-8 @md/page:mt-12" data-report-action>
          {action}
        </div>
      )}
    </div>
  );
}

export function ReportGroupSkeleton() {
  return (
    <div aria-busy="true" data-report-page="loading" className="flex flex-col">
      <p role="status" className="clip-visually">
        {w.loadingOne}
      </p>
      <SkeletonLine className="mt-4 text-small" width="w-[30%]" />
      <span className="mt-2 flex flex-col text-h1">
        <SkeletonLine width="w-full" />
        <SkeletonLine width="w-1/2" />
      </span>
      <SkeletonLine className="mt-2 text-body" width="w-[70%]" />
      <h2 className="mt-8 text-title text-ink-heading @md/page:mt-12">{w.passageTitle}</h2>
      <div className="mt-4 rounded-md border border-line">
        <Skeleton className="h-8 w-full rounded-b-none" />
        <SkeletonText className="max-w-prose p-4 text-body" widths={["w-full", "w-full", "w-full", "w-full", "w-full", "w-3/5"]} />
      </div>
    </div>
  );
}

export function PassageReportPage({ groupId }: { groupId: string }) {
  const [load, retry] = useLoad<ReportGroup>(`/api/passage-reports/${encodeURIComponent(groupId)}`);
  const trail = <Breadcrumb held trail={[{ text: copy.lessons.tabs.library, href: LESSONS_HREF }, { text: w.title, href: REPORTS_HREF }]} back={{ text: w.breadcrumbBack, href: REPORTS_HREF }} />;
  const denied = refusedAs(load, "not_a_passage_reviewer");
  useEffect(() => {
    if (denied) setPageTitle(copy.pages.lessons.title);
  }, [denied]);
  let body: ReactNode;
  if (load.status === "loading") body = <>{trail}<ReportGroupSkeleton /></>;
  else if (load.status === "error") {
    if (refusedAs(load, "unknown_group")) {
      body = (
        <>
          {trail}
          <h1 tabIndex={-1} className="clip-visually">{w.breadcrumbBack}</h1>
          <EmptyState className="mt-6" title={<Fill template={w.notFoundTitle} slots={{ id: <span className="font-mono font-medium wrap-anywhere">{groupId}</span> }} />} body={w.notFoundBody} link={{ href: REPORTS_HREF, text: w.notFoundLink }} />
        </>
      );
    } else if (denied) {
      body = (
        <>
          <h1 tabIndex={-1} className="text-h1 text-ink-heading focus:outline-none">{copy.pages.lessons.title}</h1>
          <p className="mt-2 max-w-prose text-body text-pretty text-ink-muted">{copy.pages.lessons.purpose}</p>
          <div className="mt-8">
            <NoAccess />
          </div>
        </>
      );
    } else {
      body = (
        <>
          {trail}
          <h1 tabIndex={-1} className="clip-visually">{w.breadcrumbBack}</h1>
          <div className="mt-6">
            <LoadError error={load.error} message={w.errorOne} permission={w.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </div>
        </>
      );
    }
  } else body = <ReportGroupView group={load.data} />;
  return <DocumentColumn>{body}</DocumentColumn>;
}
