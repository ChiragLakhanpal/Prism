// Writing review notes (the 35 brief, sections 5.2 and 6.1), at /drafts/new?kind=review_notes&pid=&agency=
// &version=. Nothing is saved until the writer and the verifier finish, so this page holds the writing,
// not a draft. It renders at once from the plan check Check a plan handed over: the header, the steps on
// four lines of reserved height, and the table with its activity cells filled and only the note cells
// as skeletons, sized as the notes will be. Each step is announced once. When the draft is saved, the
// page becomes the draft's page in place: the address is replaced, so Back returns to the plan check.
//
// "Stop writing" cancels the stream and goes back to the plan check, which says nothing was saved. A
// reload, or an address with no writing behind it, says I'm not writing a draft right now.
import { ENGLISH, languageName } from "../lib/lang";
import { useEffect, useId, useRef, useState } from "react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { RemovedBox, type Removed } from "../components/Checks";
import { DraftNotes, type NoteRow } from "../components/DraftNotes";
import { Skeleton } from "../components/Skeleton";
import { Steps, type Step } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { getJson } from "../lib/api";
import { formatCount, formatDate } from "../lib/format";
import { PROJECT_PAPER_STOPPED, draftScope, isPpsdKind, newKey, preloaded, startWriting, stopped, stopWriting, writing as writingStore, type Draft, type Writing } from "../lib/drafts";
import { DatesReloadCard, WritingDatesPage } from "./WritingDatesPage";
import { navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { DocumentColumn, DraftCrumbs, DraftHeader, PackageCrumbs, ppsdSubtitle, subtitleOf } from "./DraftPage";
import { FOLLOWING_HREF } from "../lib/following";
import { IdText } from "../components/ProjectId";
import { SkeletonText } from "../components/Skeleton";

const words = copy.draft;
type KindWords = (typeof copy.draft.kinds)[keyof typeof copy.draft.kinds];
const STILL_WORKING_MS = 30_000;
const short = (iso: string) => formatDate(iso, { style: "table" });

// The steps as the stream announces them. Every number in them is one the server sent.
function stepsOf(current: Writing, kind: KindWords): Step[] {
  const s = kind.steps;
  const by = Object.fromEntries(current.steps.map((step) => [step.id, step]));
  const count = by.write?.count ?? 0;
  const lines: Step[] = [
    { key: "read", running: s.read.running, done: s.read.done(formatDate(by.read?.plan_date ?? current.request.plan_date ?? "")), state: by.read?.status ?? "running" },
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
    const checks = by.check.checks ?? 0;
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

function removedItems(current: Writing, kind: KindWords): Removed[] {
  // The kind's own words for a reason first, then the answer's.
  const reasons: Record<string, { item: string; joined: string }> = { ...copy.removed.reasons, ...kind.removedReasons };
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
  const kindKey = params.get("kind");
  // A mission brief (ticket 37) is started from Following, and goes back there; suggested PPSD rows (ticket 36) from
  // the package workspace, and go back there.
  const brief = kindKey === "mission_brief";
  const pkg = isPpsdKind(kindKey) ? params.get("package") : null;
  // Planned dates (ticket 38): named by what they are drafted from, an upload or a published plan, by its id.
  const datesFrom = kindKey === "step_rows" ? params.get("from") : null;
  if (datesFrom !== null) {
    if (current && current.request.kind === "step_rows" && current.request.source === datesFrom) return <WritingDatesPage current={current} />;
    return <DatesReloadCard source={datesFrom} />;
  }
  const planHref = brief ? FOLLOWING_HREF
    : pkg ? `/packages/${encodeURIComponent(pkg)}`
      : pid && agency ? `/projects/${pid}/procurement/${agency}${version ? `/${version}` : ""}` : null;
  const matches = current !== null && (
    pkg ? current.request.kind === kindKey && current.request.package === pkg
      : current.request.project_id === pid && (brief ? current.request.kind === "mission_brief"
        : current.request.kind === (kindKey ?? "review_notes") && current.request.agency_id === agency && current.request.plan_date === version));
  if (!current || !matches) {
    const back = pkg ? copy.ppsd.backToPackage : brief ? copy.mission.backToFollowing : words.writing.backToPlan;
    const body = pkg ? copy.ppsd.reloadBody : brief ? copy.mission.reloadBody : words.writing.reloadBody;
    return (
      <DocumentColumn>
        <div data-draft-new="none">
          <h1 tabIndex={-1} className="sr-only">
            {copy.pages.draftNew.title}
          </h1>
          <EmptyState
            title={words.writing.reloadTitle}
            body={body}
            link={planHref ? { href: planHref, text: back } : { href: "/drafts", text: words.writing.reloadLink }}
          />
        </div>
      </DocumentColumn>
    );
  }
  if (brief) return <WritingBriefPage current={current} />;
  if (isPpsdKind(current.request.kind) || current.request.kind === "project_paper") {
    return <WritingKindPage current={current} backHref={planHref!} />;
  }
  return <WritingPage current={current} planHref={planHref!} />;
}

// Writing suggested PPSD rows or a Project Paper summary (ticket 36; the 36 brief, sections 5.2, 5.8 and 8.1): the
// header with the state slot and Stop writing, the steps, and the draft's shape while it is written: a skeleton block
// for each risk you selected, or the summary's three part headings as real text over body bars. When the draft is
// saved, this page becomes its page in place; Stop writing goes back to the package or the plan check, which says
// nothing was saved.
function WritingKindPage({ current, backHref }: { current: Writing; backHref: string }) {
  const ppsdKind = isPpsdKind(current.request.kind);
  const kind: KindWords = copy.draft.kinds[current.request.kind];
  const [stillWorking, setStillWorking] = useState(false);
  const opening = useRef(false);
  const pkg = current.package;
  const plan = current.summaryPlan;

  useEffect(() => {
    setPageTitle(ppsdKind ? kind.pageTitle(pkg?.title ?? "", "") : kind.pageTitle(plan?.implementing_agency ?? "", short(plan?.plan_date ?? "")));
    draftScope.set(plan?.project_id ?? null);
    return () => draftScope.set(null);
  }, [pkg, plan]);

  useEffect(() => {
    if (current.phase !== "writing") {
      setStillWorking(false);
      return;
    }
    const timer = setInterval(() => setStillWorking(Date.now() - current.lastEventAt > STILL_WORKING_MS), 1000);
    return () => clearInterval(timer);
  }, [current.phase, current.lastEventAt]);

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

  const stop = () => {
    stopWriting();
    stopped.set(ppsdKind ? backHref : `${backHref}${PROJECT_PAPER_STOPPED}`);
    window.history.back();
  };
  const tryAgain = () => startWriting({ ...current.request, idempotency_key: newKey() }, null, [], undefined, { package: pkg, summaryPlan: plan });
  const failed = current.phase === "failed" || current.phase === "dropped";
  const message = current.phase === "dropped" ? kind.writeErrors.dropped : kind.writeErrors[current.error ?? "internal"] ?? kind.writeErrors.internal;
  const retry = current.error !== "permission" && current.error !== "no_agent" && current.error !== "no_selected_risks";
  const back = ppsdKind ? copy.ppsd.backToPackage : words.writing.backToPlan;

  const by = Object.fromEntries(current.steps.map((step) => [step.id, step]));
  const s = kind.steps;
  const read = ppsdKind ? formatCount(by.read?.selected ?? pkg?.selected ?? 0) : formatDate(by.read?.plan_date ?? plan?.plan_date ?? "");
  const steps: Step[] = [{ key: "read", running: s.read.running, done: s.read.done(read), state: by.read?.status ?? "running" }];
  if (by.write) {
    const rows = by.write.rows ?? by.write.notes ?? 0;
    steps.push({
      key: "write",
      running: s.write.running(0, ""),
      done: s.write.done(by.write.sentences ?? 0, formatCount(by.write.sentences ?? 0), rows, formatCount(rows)),
      state: by.write.status,
    });
  }
  if (by.check) {
    const checks = by.check.checks ?? 0;
    steps.push({
      key: "check",
      running: words.writing.checkRunning,
      done: words.writing.checkDone(formatCount(checks), by.check.written ?? 0, formatCount(by.check.written ?? 0), by.check.removed ?? 0,
        formatCount(by.check.removed ?? 0)),
      state: by.check.status,
    });
  }
  if (by.save) steps.push({ key: "save", running: s.save.running, done: s.save.done, state: by.save.status });

  return (
    <DocumentColumn>
      <div data-draft-new={current.phase} data-writing-kind={current.request.kind} aria-busy={current.phase === "writing"}>
        {ppsdKind ? (
          <PackageCrumbs title={pkg?.title ?? ""} href={backHref} last={kind.crumb("")} />
        ) : (
          <DraftCrumbs pid={plan?.project_id ?? ""} name={plan?.project_name ?? ""} last={kind.crumb("")} />
        )}
        <DraftHeader
          className="mt-4"
          title={kind.title}
          subtitle={ppsdKind ? ppsdSubtitle(pkg?.title ?? "", pkg?.step_reference) : subtitleOf(kind, plan?.implementing_agency ?? "", plan?.plan_date ?? "")}
          state={
            current.phase === "writing" && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <p className="text-small text-ink">{words.writing.state}</p>
                <Button variant="ghost" flush onPage onClick={stop} data-stop-writing>
                  {words.writing.stop}
                </Button>
                {/* The language I write it in, when it is not English (the 42 brief, section 5.9). */}
                {current.request.lang && current.request.lang !== ENGLISH && (
                  <p className="basis-full text-caption text-ink-muted" data-writing-language>
                    {copy.draft.writingLanguage(languageName(current.request.lang))}
                  </p>
                )}
              </div>
            )
          }
        />
        <div className="mt-6">
          <Steps
            steps={failed ? steps.filter((step) => step.state === "done") : steps}
            stillWorking={stillWorking}
            reserveLines={failed || current.phase === "nothing" ? 0 : 4}
            rail={!failed && current.phase !== "nothing"}
          />
        </div>
        {current.phase === "nothing" ? (
          <div className="mt-6 max-w-prose" data-nothing-survived>
            <h2 tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
              {kind.nothingTitle}
            </h2>
            <p className="mt-2 text-body text-ink">{kind.nothingBody}</p>
            <div className="mt-4">
              <RemovedBox removed={removedItems(current, kind)} all />
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
              <Button variant="secondary" onClick={tryAgain}>
                {words.writing.tryAgain}
              </Button>
              <TextLink href={backHref}>{back}</TextLink>
            </div>
          </div>
        ) : failed ? (
          <div className="mt-6 max-w-prose" data-write-error={current.error ?? current.phase}>
            <Alert
              state="error"
              live="alert"
              action={
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  {retry && (
                    <Button variant="secondary" onClick={tryAgain}>
                      {words.writing.tryAgain}
                    </Button>
                  )}
                  <TextLink href={backHref}>{back}</TextLink>
                </div>
              }
            >
              {message}
            </Alert>
            {current.reference && retry && (
              <p className="mt-2 text-caption text-ink-muted" data-write-reference>
                <Fill template={copy.service.reference} slots={{ reference: <span className="inline-block max-w-full wrap-anywhere font-mono">{current.reference}</span> }} />
              </p>
            )}
          </div>
        ) : ppsdKind ? (
          <ol aria-hidden="true" className="mt-6 flex flex-col gap-3" data-writing-rows>
            {Array.from({ length: Math.max(pkg?.selected ?? 1, 1) }, (_, index) => (
              <li key={index} className="h-55 rounded-md border border-line bg-surface p-4">
                <SkeletonText className="text-small" widths={["w-2/5"]} />
                <div className="mt-3 flex flex-col gap-2">
                  <Skeleton className="h-3.5 w-full" />
                  <Skeleton className="h-3.5 w-11/12" />
                  <Skeleton className="h-3.5 w-3/5" />
                </div>
                <Skeleton className="mt-4 h-8 w-36" radius="rounded-pill" />
              </li>
            ))}
          </ol>
        ) : (
          <section aria-label={copy.paper.writingParts} className="mt-6 rounded-md border border-line bg-surface p-4 md:p-8" data-paper-parts="writing">
            <div className="flex flex-col gap-8">
              {["plan", "record", "ppsd"].map((part) => (
                <div key={part}>
                  <h3 className="text-title text-ink-heading">{copy.paper.parts[part]}</h3>
                  <div aria-hidden="true" className="mt-2">
                    <SkeletonText className="text-body" widths={["w-full", "w-[96%]", "w-[90%]", "w-[55%]"]} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </DocumentColumn>
  );
}

function WritingPage({ current, planHref }: { current: Writing; planHref: string }) {
  const kind: KindWords = copy.draft.kinds[current.request.kind];
  const ledeId = useId();
  const [stillWorking, setStillWorking] = useState(false);
  const opening = useRef(false);
  const plan = current.plan!.plan!;
  const project = current.plan!.project!;

  useEffect(() => {
    setPageTitle(kind.pageTitle(plan.implementing_agency, short(plan.plan_date)));
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
  // Trying again can't help when the viewer can't read the plan or no writer is connected.
  const retry = current.error !== "permission" && current.error !== "no_agent";
  const steps = stepsOf(current, kind);
  return (
    <DocumentColumn>
      <div data-draft-new={current.phase} aria-busy={current.phase === "writing"}>
        <DraftCrumbs pid={project.project_id} name={project.project_name} last={kind.title} />
        <DraftHeader
          className="mt-4"
          title={kind.title}
          subtitle={subtitleOf(kind, plan.implementing_agency, plan.plan_date)}
          state={
            current.phase === "writing" && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <p className="text-small text-ink">{words.writing.state}</p>
                <Button variant="ghost" flush onPage onClick={stop} data-stop-writing>
                  {words.writing.stop}
                </Button>
                {/* The language I write it in, when it is not English (the 42 brief, section 5.9). */}
                {current.request.lang && current.request.lang !== ENGLISH && (
                  <p className="basis-full text-caption text-ink-muted" data-writing-language>
                    {copy.draft.writingLanguage(languageName(current.request.lang))}
                  </p>
                )}
              </div>
            )
          }
        />
        <div className="mt-6">
          {/* Four lines are kept while the steps stream in, so they never push the table down; once
              writing has stopped, the space goes, and so does the icon rail, since no step is running. */}
          <Steps
            steps={failed ? steps.filter((step) => step.state === "done") : steps}
            stillWorking={stillWorking}
            reserveLines={failed || current.phase === "nothing" ? 0 : 4}
            rail={!failed && current.phase !== "nothing"}
          />
        </div>
        {current.phase === "nothing" ? (
          <div className="mt-6 max-w-prose" data-nothing-survived>
            <h2 tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
              {kind.nothingTitle}
            </h2>
            <p className="mt-2 text-body text-ink">{kind.nothingBody}</p>
            <div className="mt-4">
              <RemovedBox removed={removedItems(current, kind)} all />
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
                  {retry && (
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
            {current.reference && retry && (
              <p className="mt-2 text-caption text-ink-muted" data-write-reference>
                <Fill template={copy.service.reference} slots={{ reference: <span className="inline-block max-w-full wrap-anywhere font-mono">{current.reference}</span> }} />
              </p>
            )}
          </div>
        ) : (
          <>
            <p id={ledeId} className="sr-only">
              {kind.tableCaption(plan.implementing_agency, formatDate(plan.plan_date))}
            </p>
            <div className="mt-6">
              <DraftNotes
                rows={rows}
                columns={Object.values(kind.columns)}
                caption={kind.tableCaption(plan.implementing_agency, formatDate(plan.plan_date))}
                cardsLabelId={ledeId}
              />
            </div>
          </>
        )}
      </div>
    </DocumentColumn>
  );
}

// Writing a mission brief (ticket 37; the 37 brief, section 7.1): the header with the state slot and Stop writing,
// the steps, and the five part headings as real text, each with two sentence bars and a table's place, until the
// draft is saved and this page becomes its page in place. "Stop writing" goes back to Following, which says
// nothing was saved.
const PARTS = ["plans", "awards", "ratings", "disbursement", "closing"];

function briefSteps(current: Writing): Step[] {
  const s = copy.draft.kinds.mission_brief.steps;
  const by = Object.fromEntries(current.steps.map((step) => [step.id, step]));
  const read = by.read ?? {};
  const counted = (n: number | undefined) => [n ?? 0, formatCount(n ?? 0)] as const;
  const lines: Step[] = [{
    key: "read",
    running: s.read.running,
    done: s.read.counted(...counted(read.plans), ...counted(read.awards), ...counted(read.isrs)),
    state: by.read?.status ?? "running",
  }];
  if (by.write) {
    lines.push({
      key: "write",
      running: s.write.running(0, ""),
      state: by.write.status,
      done: s.write.done(by.write.sentences ?? 0, formatCount(by.write.sentences ?? 0), 0, ""),
    });
  }
  if (by.check) {
    const checks = by.check.checks ?? 0;
    lines.push({
      key: "check",
      running: words.writing.checkRunning,
      state: by.check.status,
      done: words.writing.checkDone(formatCount(checks), by.check.written ?? 0, formatCount(by.check.written ?? 0), by.check.removed ?? 0,
        formatCount(by.check.removed ?? 0)),
    });
  }
  if (by.save) lines.push({ key: "save", running: s.save.running, done: s.save.done, state: by.save.status });
  return lines;
}

function WritingBriefPage({ current }: { current: Writing }) {
  const kind = copy.draft.kinds.mission_brief;
  const project = current.project!;
  const [stillWorking, setStillWorking] = useState(false);
  const opening = useRef(false);

  useEffect(() => {
    setPageTitle(kind.pageTitle(project.project_name, project.project_id));
    draftScope.set(project.project_id);
    return () => draftScope.set(null);
  }, [project]);

  useEffect(() => {
    if (current.phase !== "writing") {
      setStillWorking(false);
      return;
    }
    const timer = setInterval(() => setStillWorking(Date.now() - current.lastEventAt > STILL_WORKING_MS), 1000);
    return () => clearInterval(timer);
  }, [current.phase, current.lastEventAt]);

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

  const stop = () => {
    stopWriting();
    stopped.set(FOLLOWING_HREF);
    window.history.back();
  };
  const tryAgain = () => startWriting({ ...current.request, idempotency_key: newKey() }, null, [], project);
  const failed = current.phase === "failed" || current.phase === "dropped";
  const message = current.phase === "dropped" ? kind.writeErrors.dropped : kind.writeErrors[current.error ?? "internal"] ?? kind.writeErrors.internal;
  const retry = current.error !== "permission" && current.error !== "no_agent";
  const steps = briefSteps(current);
  return (
    <DocumentColumn>
      <div data-draft-new={current.phase} aria-busy={current.phase === "writing"}>
        <DraftCrumbs pid={project.project_id} name={project.project_name} last={kind.title} />
        <DraftHeader
          className="mt-4"
          title={kind.title}
          subtitle={<Fill template={kind.subtitle} slots={{ name: project.project_name, pid: <IdText id={project.project_id} />, country: project.country ?? "" }} />}
          state={
            current.phase === "writing" && (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <p className="text-small text-ink">{words.writing.state}</p>
                <Button variant="ghost" flush onPage onClick={stop} data-stop-writing>
                  {words.writing.stop}
                </Button>
                {/* The language I write it in, when it is not English (the 42 brief, section 5.9). */}
                {current.request.lang && current.request.lang !== ENGLISH && (
                  <p className="basis-full text-caption text-ink-muted" data-writing-language>
                    {copy.draft.writingLanguage(languageName(current.request.lang))}
                  </p>
                )}
              </div>
            )
          }
        />
        <div className="mt-6">
          <Steps
            steps={failed ? steps.filter((step) => step.state === "done") : steps}
            stillWorking={stillWorking}
            reserveLines={failed || current.phase === "nothing" ? 0 : 4}
            rail={!failed && current.phase !== "nothing"}
          />
        </div>
        {current.phase === "nothing" ? (
          <div className="mt-6 max-w-prose" data-nothing-survived>
            <h2 tabIndex={-1} className="text-title text-ink-heading focus:outline-none">
              {kind.nothingTitle}
            </h2>
            <p className="mt-2 text-body text-ink">{kind.nothingBody}</p>
            <div className="mt-4">
              <RemovedBox removed={removedItems(current, kind)} all />
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
              <Button variant="secondary" onClick={tryAgain}>
                {words.writing.tryAgain}
              </Button>
              <TextLink href={FOLLOWING_HREF}>{copy.mission.backToFollowing}</TextLink>
            </div>
          </div>
        ) : failed ? (
          <div className="mt-6 max-w-prose" data-write-error={current.error ?? current.phase}>
            <Alert
              state="error"
              live="alert"
              action={
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  {retry && (
                    <Button variant="secondary" onClick={tryAgain}>
                      {words.writing.tryAgain}
                    </Button>
                  )}
                  <TextLink href={FOLLOWING_HREF}>{copy.mission.backToFollowing}</TextLink>
                </div>
              }
            >
              {message}
            </Alert>
          </div>
        ) : (
          <section aria-label={copy.mission.writingParts} className="mt-8 flex flex-col gap-12" data-brief-parts="writing">
            {PARTS.map((part) => (
              <div key={part}>
                <h3 className="text-title text-ink-heading">{copy.mission.parts[part]}</h3>
                <div aria-hidden="true" className="mt-2">
                  <SkeletonText className="text-body" widths={["w-full", "w-[70%]"]} />
                  <Skeleton className="mt-4 h-16 w-full" />
                </div>
              </div>
            ))}
          </section>
        )}
      </div>
    </DocumentColumn>
  );
}
