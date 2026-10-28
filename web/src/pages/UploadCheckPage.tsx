// An upload's check (ticket 38; the 38 brief, sections 3.4, 5.4 and 5.5), at /packages/uploads/:uploadId: brief 10's
// Check a plan page on the team's private upload, with the access label under the subtitle, a line that says how the
// file was read, and the action that drafts a planned date for every STEP step. The server checks the upload again on
// today's records. An upload of another team, or one that does not exist, gets the same card.
import { useEffect, useId, useState, type ReactNode } from "react";
import { AccessLabel } from "../components/AccessLabel";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { EightColumns } from "../components/EightColumns";
import { LoadError } from "../components/LoadError";
import { checkPill, PlanCheck, PlanCheckHeader, PlanCheckSkeleton, type CheckedPlan } from "../components/PlanCheck";
import { Source } from "../components/Source";
import { copy } from "../copy";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";
import { startDates } from "../lib/drafts";
import { navigate } from "../lib/router";
import { setPageTitle } from "../lib/title";
import type { UploadCheck } from "../lib/uploads";
import { viewOf } from "../lib/view";
import { useRowsLoading } from "../lib/planRows";

const words = copy.uploadCheck;
const short = (iso: string) => formatDate(iso, { style: "table" });

function Reading({ upload, name }: { upload: UploadCheck["upload"]; name: string }) {
  const [open, setOpen] = useState(false);
  const panel = useId();
  const reading = upload.reading;
  return (
    <div className="mt-2" data-reading-line>
      <p className="text-body text-ink">
        {words.readLine(reading.activities, formatCount(reading.activities), upload.file_name, name, upload.project_id)}
      </p>
      <Button variant="ghost" aria-expanded={open} aria-controls={panel} onClick={() => setOpen(!open)} className="mt-2">
        {open ? words.howHide : words.howShow}
      </Button>
      {open && (
        <div id={panel} className="mt-2 flex flex-col gap-2 text-small text-ink" data-how-read>
          {reading.sheets.length > 0 && <p>{words.sheets(reading.sheets)}</p>}
          <p className="font-semibold">{words.used}</p>
          <ul className="list-disc pl-4">
            {reading.used.map((entry) => (
              <li key={entry.header}>{entry.as ? words.usedAs(entry.header, entry.as) : entry.header}</li>
            ))}
          </ul>
          {reading.unused.length > 0 && (
            <>
              <p className="font-semibold">{words.unused}</p>
              <ul className="list-disc pl-4">
                {reading.unused.map((header) => (
                  <li key={header}>{header}</li>
                ))}
              </ul>
            </>
          )}
          {reading.unread_values > 0 && <p>{words.values(reading.unread_values, formatCount(reading.unread_values))}</p>}
        </div>
      )}
    </div>
  );
}

export function UploadCheckPage({ uploadId, search }: { uploadId: string; search: string }) {
  const view = viewOf(search);
  const preview = view === "piu" || view === "public";
  const [load, retry] = useLoad<UploadCheck>(`/api/uploads/${encodeURIComponent(uploadId)}${preview ? `?view=${view}` : ""}`);
  const slotId = useId();
  const result = load.status === "ready" ? load.data : null;
  const checked = result && !result.abstention && result.plan && result.project && result.counts ? (result as UploadCheck & CheckedPlan) : null;
  // A link that opens a row's records waits while the check loads, then says if the page holds none (ticket 100's
  // review, F2).
  const rowsLoading = load.status === "loading";
  useRowsLoading(rowsLoading);
  useEffect(() => {
    if (checked) setPageTitle(words.crumb(short(checked.upload.uploaded_on)));
  }, [checked]);

  const crumbs = (last: ReactNode) => [{ text: copy.nav.tabs.packages, href: "/packages" }, { text: last }];
  let body: ReactNode;
  let trail = crumbs(copy.pages.uploadCheck.title);
  if (load.status === "loading") {
    body = (
      <>
        <PlanCheckHeader agency={copy.pages.uploadCheck.title} sticky={false} />
        <AccessLabel className="mt-2" />
        <PlanCheckSkeleton slow={load.slow} />
      </>
    );
  } else if (load.status === "error" && load.error?.status === 404) {
    body = (
      <EightColumns className="mt-2">
        <h1 tabIndex={-1} className="sr-only">{copy.pages.uploadCheck.title}</h1>
        <EmptyState title={words.notFoundTitle} body={words.notFoundBody} link={{ href: "/packages", text: words.notFoundLink }} />
      </EightColumns>
    );
  } else if (load.status === "error") {
    body = (
      <>
        <PlanCheckHeader agency={copy.pages.uploadCheck.title} />
        <EightColumns className="mt-6">
          <LoadError error={load.error} message={words.error} permission={words.error} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </EightColumns>
      </>
    );
  } else if (checked) {
    const upload = checked.upload;
    trail = crumbs(words.crumb(short(upload.uploaded_on)));
    const count = checked.counts.activities;
    const start = () => navigate(startDates(upload, checked));
    body = (
      <>
        <PlanCheckHeader
          agency={checked.plan.implementing_agency}
          plan={upload.uploader.you ? words.subtitleYou(formatDate(upload.uploaded_on))
            : words.subtitleTeammate(formatDate(upload.uploaded_on), upload.uploader.name ?? "")}
          pill={checkPill(checked)}
          // The head sticks only while it holds the page's one action (DESIGN.md section 5, Page head; ticket 100).
          sticky={!preview}
          action={preview ? undefined : (
            <Button variant="primary" onClick={start} aria-describedby={`${slotId}-description ${slotId}-feedforward`} data-dates-action>
              {/* A button's count is a numeral (DESIGN.md section 7). */}
              {words.datesButton(count, formatNumber(count, { compact: false }))}
            </Button>
          )}
          feedforward={preview ? undefined : (
            <>
              <p id={`${slotId}-feedforward`} className="text-caption text-ink-muted @lg/page:text-right">{words.datesFeedforward}</p>
              <span id={`${slotId}-description`} className="sr-only">{words.datesDescription}</span>
            </>
          )}
        />
        <AccessLabel className="mt-2" />
        <PlanCheck
          result={checked}
          method={<p className="text-body text-ink">{words.method}</p>}
          afterMethod={<Reading upload={upload} name={checked.project.display_name ?? checked.project.project_name} />}
          source={
            <Source>
              {copy.uploadCheck.meta(formatDate(upload.uploaded_on), upload.upload_id)}
            </Source>
          }
        />
      </>
    );
  } else {
    body = (
      <EightColumns className="mt-2">
        <h1 tabIndex={-1} className="sr-only">{copy.pages.uploadCheck.title}</h1>
        <EmptyState title={words.notFoundTitle} body={words.notFoundBody} link={{ href: "/packages", text: words.notFoundLink }} />
      </EightColumns>
    );
  }
  return (
    <div data-upload-check-page={load.status}>
      <Breadcrumb trail={trail} />
      <div>{body}</div>
    </div>
  );
}
