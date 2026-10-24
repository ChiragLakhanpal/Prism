// Writing review notes (the 35 brief, sections 5.2 and 6.1), at /drafts/new?kind=review_notes&pid=&agency=
// &version=. Nothing is saved until the writer and the verifier finish, so this page holds the writing,
// not a draft. It renders at once from the plan check Check a plan handed over: the header, the steps on
// four lines of reserved height, and the table with its activity cells filled and only the note cells
// as skeletons, sized as the notes will be. Each step is announced once. When the draft is saved, the
// page becomes the draft's page in place: the address is replaced, so Back returns to the plan check.
//
// "Stop writing" cancels the stream and goes back to the plan check, which says nothing was saved. A
// reload, or an address with no writing behind it, says I'm not writing a draft right now.
import { useEffect, useId, useRef, useState } from "react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { RemovedBox, type Removed } from "../components/Checks";
import { DraftNotes, type NoteRow } from "../components/DraftNotes";
import { Skeleton } from "../components/Skeleton";
import { Steps, type Step } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { getJson } from "../lib/api";
import { formatCount, formatDate } from "../lib/format";
import { draftScope, newKey, preloaded, startWriting, stopped, stopWriting, writing as writingStore, type Draft, type Writing } from "../lib/drafts";
import { navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { DocumentColumn, DraftCrumbs, DraftHeader, subtitleOf } from "./DraftPage";

const words = copy.draft;
const kind = copy.draft.kinds.review_notes;
const STILL_WORKING_MS = 30_000;
const short = (iso: string) => formatDate(iso, { style: "table" });

function stepsOf(current: Writing): Step[] {
  const s = kind.steps;
  const by = Object.fromEntries(current.steps.map((step) => [step.id, step]));
  const count = current.rows.length;
  const lines: Step[] = [
    { key: "read", running: s.read.running, done: s.read.done(formatDate(by.read?.plan_date ?? current.request.plan_date)), state: by.read?.status ?? "running" },
  ];
  if (by.write) {
    lines.push({
      key: "write",
      running: s.write.running(count, formatCount(count)),
      done: s.write.done(by.write.sentences ?? 0, formatCount(by.write.sentences ?? 0), by.write.notes ?? 0, formatCount(by.write.notes ?? 0)),
      state: by.write.status,
    });
  }
  if (by.check) {
    const checks = by.check.checks_run?.length ?? 0;
    lines.push({
      key: "check",
      running: words.writing.checkRunning,
      done: words.writing.checkDone(formatCount(checks), by.check.written ?? 0, formatCount(by.check.written ?? 0), by.check.removed ?? 0,
        formatCount(by.check.removed ?? 0)),
      state: by.check.status,
    });
  }
  if (by.save) lines.push({ key: "save", running: s.save.running, done: s.save.done, state: by.save.status });
  return lines;
}

function removedItems(current: Writing): Removed[] {
  const reasons = copy.removed.reasons as Record<string, { item: string; joined: string }>;
  return current.removed.map((item) => {
    const code = [item.reason, ...item.reasons.map((reason) => reason.code)].find((one) => one in reasons);
    const reason = code ? reasons[code] : copy.removed.unknownReason;
    return { sentence: item.sentence, reason: reason.item, reasonJoined: reason.joined };
  });
}

export function DraftNewPage({ search }: { search: string }) {
  const current = useStore(writingStore);
  const params = new URLSearchParams(search);
  const pid = params.get("pid");
  const agency = params.get("agency");
  const version = params.get("version");
  const planHref = pid && agency ? `/projects/${pid}/procurement/${agency}${version ? `/${version}` : ""}` : null;
  const matches = current !== null && current.request.project_id === pid && current.request.agency_id === agency &&
    current.request.plan_date === version;
  if (!current || !matches) {
    return (
      <DocumentColumn>
        <div data-draft-new="none">
          <h1 tabIndex={-1} className="sr-only">
            {copy.pages.draftNew.title}
          </h1>
          <EmptyState
            title={words.writing.reloadTitle}
            body={words.writing.reloadBody}
            link={planHref ? { href: planHref, text: words.writing.backToPlan } : { href: "/drafts", text: words.writing.reloadLink }}
          />
        </div>
      </DocumentColumn>
    );
  }
  return <WritingPage current={current} planHref={planHref!} />;
}

function WritingPage({ current, planHref }: { current: Writing; planHref: string }) {
  const ledeId = useId();
  const [stillWorking, setStillWorking] = useState(false);
  const opening = useRef(false);
  const plan = current.plan.plan!;
  const project = current.plan.project!;

  useEffect(() => {
    document.title = copy.pageTitle(kind.pageTitle(plan.implementing_agency, short(plan.plan_date)));
    // The box carries the draft's project as its scope chip here too.
    draftScope.set(plan.project_id);
    return () => draftScope.set(null);
  }, [plan]);

  // "I'm still working on this step." after 30 seconds with no event (brief 14).
  useEffect(() => {
    if (current.phase !== "writing") {
      setStillWorking(false);
      return;
    }
    const timer = setInterval(() => setStillWorking(Date.now() - current.lastEventAt > STILL_WORKING_MS), 1000);
    return () => clearInterval(timer);
  }, [current.phase, current.lastEventAt]);

  // Saved: read the draft once, hand it to the draft's page, and become that page in place.
  useEffect(() => {
    if (current.phase !== "done" || !current.draftId || opening.current) return;
    opening.current = true;
    const id = current.draftId;
    getJson<Draft>(`/api/drafts/${encodeURIComponent(id)}`).then(
      (draft) => {
        preloaded.set((all) => ({ ...all, [id]: draft }));
        navigate(`/drafts/${encodeURIComponent(id)}`, { replace: true, quiet: true });
      },
      () => navigate(`/drafts/${encodeURIComponent(id)}`, { replace: true, quiet: true }),
    );
  }, [current.phase, current.draftId]);

  // Back to the plan check, whose history entry this page followed, with its notice that nothing was saved.
  const stop = () => {
    stopWriting();
    stopped.set(planHref);
    window.history.back();
  };
  // The same request again, under a new key, since the first one saved nothing.
  const tryAgain = () => startWriting({ ...current.request, idempotency_key: newKey() }, current.plan, current.rows);

  const rows: NoteRow[] = current.rows.map((row) => {
    const mark = row.marks.some((one) => one.mark === "needs_a_look") ? "needs_a_look" : "watch";
    return {
      key: row.activity_reference_no,
      mark,
      description: row.description,
      href: `${planHref}#${row.activity_reference_no}`,
      // The note's skeleton: three static bars at 100, 92 and 60 percent of the cell, 8 px apart.
      note: (
        <div aria-hidden="true" className="flex flex-col gap-2">
          <Skeleton className="h-3.5 w-full" />
          <Skeleton className="h-3.5 w-11/12" />
          <Skeleton className="h-3.5 w-3/5" />
        </div>
      ),
    };
  });

  const failed = current.phase === "failed" || current.phase === "dropped";
  const message = current.phase === "dropped" ? kind.writeErrors.dropped : kind.writeErrors[current.error ?? "internal"] ?? kind.writeErrors.internal;
  const steps = stepsOf(current);
  return (
    <DocumentColumn>
      <div data-draft-new={current.phase} aria-busy={current.phase === "writing"}>
        <DraftCrumbs pid={project.project_id} name={project.project_name} last={kind.title} />
        <div className="mt-4">
          <DraftHeader
            title={kind.title}
            subtitle={subtitleOf(plan.implementing_agency, plan.plan_date)}
            state={
              current.phase === "writing" && (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <p className="text-small text-ink">{words.writing.state}</p>
                  <Button variant="ghost" onClick={stop} data-stop-writing>
                    {words.writing.stop}
                  </Button>
                </div>
              )
            }
          />
        </div>
        <div className="mt-6">
          <Steps steps={failed ? steps.filter((step) => step.state === "done") : steps} stillWorking={stillWorking} reserveLines={4} rail={!failed} />
        </div>
        {current.phase === "nothing" ? (
          <div className="mt-6 max-w-prose" data-nothing-survived>
            <h2 tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
              {kind.nothingTitle}
            </h2>
            <p className="mt-2 text-body text-ink">{kind.nothingBody}</p>
            <div className="mt-4">
              <RemovedBox removed={removedItems(current)} all />
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
              <Button variant="secondary" onClick={tryAgain}>
                {words.writing.tryAgain}
              </Button>
              <TextLink href={planHref}>{words.writing.backToPlan}</TextLink>
            </div>
          </div>
        ) : failed ? (
          <div className="mt-6 max-w-prose" data-write-error={current.error ?? current.phase}>
            <Alert
              state="error"
              live="alert"
              action={
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  {current.error !== "permission" && (
                    <Button variant="secondary" onClick={tryAgain}>
                      {words.writing.tryAgain}
                    </Button>
                  )}
                  <TextLink href={planHref}>{words.writing.backToPlan}</TextLink>
                </div>
              }
            >
              {message}
            </Alert>
          </div>
        ) : (
          <>
            <p id={ledeId} className="sr-only">
              {kind.tableCaption(plan.implementing_agency, formatDate(plan.plan_date))}
            </p>
            <div className="mt-6">
              <DraftNotes rows={rows} caption={kind.tableCaption(plan.implementing_agency, formatDate(plan.plan_date))} cardsLabelId={ledeId} />
            </div>
          </>
        )}
      </div>
    </DocumentColumn>
  );
}
