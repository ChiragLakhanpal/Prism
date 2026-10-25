// Writing planned dates (ticket 38; the 38 brief, sections 5.7 and 6.6), at /drafts/new?kind=step_rows&from={source}:
// no model writes them, so the page lists the server's steps (reading the activities and finding comparable packages,
// checking every date and count, saving) and nothing is saved until the verifier finishes. When the draft is saved,
// the address is replaced with the draft's, so Back returns to the upload's check. When no step could be dated, the
// page says so and that I saved no draft; "Stop writing" goes back and saves nothing.
import { useEffect } from "react";
import { AccessLabel } from "../components/AccessLabel";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { Steps, type Step } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { formatCount, formatDate } from "../lib/format";
import { draftHref, stopWriting, type Writing } from "../lib/drafts";
import { navigate } from "../lib/router";
import { setPageTitle } from "../lib/title";
import { DocumentColumn, DraftCrumbs, DraftHeader } from "./DraftPage";

const kind = copy.draft.kinds.step_rows;
const words = copy.draft;

function backOf(source: string): string {
  return source.startsWith("upload:") ? `/packages/uploads/${encodeURIComponent(source.slice("upload:".length))}` : "/packages";
}

export function DatesReloadCard({ source }: { source: string }) {
  return (
    <DocumentColumn>
      <div data-draft-new="none">
        <h1 tabIndex={-1} className="sr-only">
          {kind.title}
        </h1>
        <EmptyState title={words.writing.reloadTitle} body={words.writing.reloadBody}
          link={{ href: backOf(source), text: copy.uploadCheck.backToCheck }} />
      </div>
    </DocumentColumn>
  );
}

export function WritingDatesPage({ current }: { current: Writing }) {
  const plan = current.datesPlan;
  const back = plan?.back ?? backOf(current.request.source ?? "");
  useEffect(() => {
    setPageTitle(kind.pageTitle(plan?.implementing_agency ?? "", formatDate(plan?.date ?? "", { style: "table" })));
  }, [plan]);
  useEffect(() => {
    if (current.phase === "done" && current.draftId) navigate(draftHref(current.draftId), { replace: true });
  }, [current.phase, current.draftId]);

  const by = Object.fromEntries(current.steps.map((step) => [step.id, step]));
  const count = by.read && "activities" in by.read ? Number((by.read as { activities?: number }).activities ?? 0) : 0;
  const steps: Step[] = [{ key: "read", running: kind.steps.read.running, done: kind.steps.read.done(formatCount(count)), state: by.read?.status ?? "running" }];
  if (by.check) steps.push({ key: "check", running: kind.steps.write.running(0, ""), done: kind.steps.write.running(0, ""), state: by.check.status });
  if (by.save) steps.push({ key: "save", running: kind.steps.save.running, done: kind.steps.save.done, state: by.save.status });

  const stop = () => {
    stopWriting();
    navigate(back);
  };
  return (
    <DocumentColumn>
      <div data-draft-new={current.phase}>
        {plan && <DraftCrumbs pid={plan.project_id} name={plan.project_name} last={kind.crumb(formatDate(plan.date, { style: "table" }))} />}
        <DraftHeader
          className="mt-4"
          title={kind.title}
          subtitle={<Fill template={kind.subtitle} slots={{ agency: plan?.implementing_agency ?? "", date: formatDate(plan?.date ?? "") }} />}
          state={null}
        />
        <AccessLabel className="mt-2" />
        {current.phase === "writing" && (
          <div className="mt-6 flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-4">
              <p className="text-small text-ink">{words.writing.state}</p>
              <Button variant="ghost" onClick={stop}>{words.writing.stop}</Button>
            </div>
            <Steps steps={steps} reserveLines={3} />
          </div>
        )}
        {current.phase === "nothing" && (
          <div className="mt-6 max-w-[72ch]" data-nothing-dated>
            <h2 className="text-title text-ink-heading">{kind.nothingTitle}</h2>
            <p className="mt-2 text-body text-ink">
              <Fill template={kind.nothingBody} slots={{ min: String(current.nothingDated?.min_comparables ?? "") }} />{" "}
              <TextLink href={back}>{copy.uploadCheck.backToCheck}</TextLink>
            </p>
          </div>
        )}
        {(current.phase === "failed" || current.phase === "dropped") && (
          <div className="mt-6 flex max-w-[72ch] flex-col gap-3">
            <Alert state="error" live="alert">
              {current.phase === "dropped" ? kind.writeErrors.dropped : (kind.writeErrors[current.error ?? ""] ?? kind.writeErrors.internal)}
            </Alert>
            <TextLink href={back}>{copy.uploadCheck.backToCheck}</TextLink>
          </div>
        )}
      </div>
    </DocumentColumn>
  );
}
