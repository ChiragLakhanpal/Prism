// Check my plan (ticket 38; the 38 brief, sections 3.2, 5.2, 5.3 and 6.1), at /packages/check: an implementing agency
// officer uploads the Procurement Plan they are preparing, or picks one of their agency's published plans. The access
// label and the privacy sentences sit above the file field, before anything is chosen, and the button says beside it
// that uploading submits nothing. Nothing is kept until the server has read and checked the file; a reading that fails
// says why and that I kept nothing. When the check is kept, the page moves to the upload's check, replacing this entry,
// so Back returns here.
//
// The file goes to the server as the request's body (src/strata/server/uploads.py), with the project and the file's
// name in the address. The STEP column names the page lists come from the server's STEP column registry.
import { useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AccessLabel } from "../components/AccessLabel";
import { Alert } from "../components/Alert";
import { Breadcrumb } from "../components/Breadcrumb";
import { Button } from "../components/Button";
import { EmptyState } from "../components/Card";
import { Fill } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { PageHeader } from "../components/PageHeader";
import { Skeleton } from "../components/Skeleton";
import { Steps } from "../components/Steps";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { ApiError } from "../lib/api";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { useLoad } from "../lib/load";
import { newKey } from "../lib/drafts";
import { navigate } from "../lib/router";
import { endingOf, sendUpload, uploadHref, type UploadForm, type UploadRefusal } from "../lib/uploads";
import { viewOf } from "../lib/view";

const words = copy.upload;
const short = (iso: string) => formatDate(iso, { style: "table" });

export function sizeText(bytes: number): string {
  return bytes < 1_000_000
    ? words.sizeKb(formatNumber(bytes / 1024, { decimals: 1, compact: false }))
    : words.sizeMb(formatNumber(bytes / 1_048_576, { decimals: 1, compact: false }));
}

function refusalText(refusal: UploadRefusal, name: string): string {
  if (refusal.code === "missing_columns") {
    const missing = refusal.missing ?? [];
    const list = words.missingList(missing);
    return missing.length === 1 ? words.errors.missing_one(name, list) : words.errors.missing_many(name, list);
  }
  if (refusal.code === "too_many_rows") return words.errors.too_many_rows(name, formatCount(refusal.n ?? 0), formatCount(refusal.max_rows ?? 0));
  const say = words.errors[refusal.code] ?? words.errors.service;
  return say(name);
}

// "Show the columns I read": STEP's column names from the server's registry, in place, inside the card.
function ColumnLists({ form, open = false, headingLevel }: { form: UploadForm; open?: boolean; headingLevel?: 2 }) {
  const [shown, setShown] = useState(open);
  const panel = useId();
  const lists = (
    <div id={panel} className="mt-2 flex flex-col gap-2 text-small text-ink" data-column-lists>
      {headingLevel && <h2 className="text-title text-ink-heading">{words.columnsHeading}</h2>}
      <p>{words.columnsIntro}</p>
      <p className="font-semibold">{words.columnsRequired}</p>
      <ul className="list-disc pl-4">
        {form.columns.needed.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
      <p className="font-semibold">{words.columnsOptional}</p>
      <ul className="list-disc pl-4">
        {form.columns.optional.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
      <p>{words.columnsOther}</p>
    </div>
  );
  if (open) return lists;
  return (
    <div className="mt-2">
      <Button variant="ghost" aria-expanded={shown} aria-controls={panel} onClick={() => setShown(!shown)} data-columns-toggle>
        {shown ? words.columnsHide : words.columnsShow}
      </Button>
      {shown && lists}
    </div>
  );
}

// A failed upload: the server's refusal, or none when the connection dropped before it answered.
type Phase = { state: "form" } | { state: "reading"; name: string } | { state: "failed"; refusal: UploadRefusal | null; name: string; reference: string | null };

export function CheckMyPlanPage({ search }: { search: string }) {
  const view = viewOf(search);
  const preview = view === "piu" || view === "public";
  const [load, retry] = useLoad<UploadForm>(`/api/uploads/form${preview ? `?view=${view}` : ""}`);
  const crumbs = [{ text: copy.nav.tabs.packages, href: "/packages" }, { text: words.crumb }];
  const header = <PageHeader title={words.title} purpose={words.purpose} />;

  let body: ReactNode;
  if (load.status === "loading") {
    body = (
      <div className="mt-6 flex flex-col gap-4" data-check-my-plan="loading">
        <Skeleton className="h-11 w-full max-w-[640px]" />
        <Skeleton className="h-[68px] w-full max-w-[640px]" />
        <p role="status" className="sr-only">
          {words.loading}
        </p>
      </div>
    );
  } else if (load.status === "error") {
    body = (
      <div className="mt-6 max-w-[72ch]">
        <LoadError error={load.error} message={words.loadError} permission={words.loadError} onRetry={retry}
          retrying={load.retrying} attempt={load.attempt} />
      </div>
    );
  } else if (!load.data.officer && !load.data.preview) {
    body = (
      <EmptyState className="mt-6 max-w-[72ch]" title={words.notOfficerTitle} body={words.notOfficerBody}
        link={{ href: "/projects", text: words.notOfficerLink }} />
    );
  } else if (load.data.officer && load.data.projects.length === 0) {
    body = <EmptyState className="mt-6 max-w-[72ch]" title={words.noProjectTitle(load.data.agency?.name ?? "")} body={words.noProjectBody} />;
  } else {
    body = <UploadCard form={load.data} preview={load.data.preview} />;
  }
  return (
    <div className="layout-grid" data-check-my-plan-page={load.status}>
      <div className="col-span-12 @xl/page:col-span-7">
        <Breadcrumb trail={crumbs} />
        <div className="mt-4">{header}</div>
        {body}
      </div>
    </div>
  );
}

function UploadCard({ form, preview }: { form: UploadForm; preview: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [project, setProject] = useState(form.projects.length === 1 ? form.projects[0].project_id : "");
  const [errors, setErrors] = useState<{ project?: string; file?: string }>({});
  const [phase, setPhase] = useState<Phase>({ state: "form" });
  const key = useRef(newKey());
  const fileInput = useRef<HTMLInputElement>(null);
  const projectInput = useRef<HTMLSelectElement>(null);
  const id = useId();
  const agency = form.agency?.name ?? "";
  const chosen = form.projects.find((one) => one.project_id === project);

  const check = (picked: File | null): string | undefined => {
    if (!picked) return words.errorNone;
    if (!form.limits.accept.includes(endingOf(picked.name))) return words.errorType(picked.name, endingOf(picked.name) || picked.name);
    if (picked.size === 0) return words.errorEmpty(picked.name);
    if (picked.size > form.limits.max_size_bytes) return words.errorSize(picked.name, sizeText(picked.size), sizeText(form.limits.max_size_bytes));
    return undefined;
  };

  const choose = (picked: File | null) => {
    setFile(picked);
    setErrors((current) => ({ ...current, file: picked ? check(picked) : undefined }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (preview) return;
    const found = { project: project ? undefined : words.projectError, file: check(file) };
    setErrors(found);
    if (found.project) return projectInput.current?.focus();
    if (found.file) return fileInput.current?.focus();
    setPhase({ state: "reading", name: file!.name });
    try {
      const kept = await sendUpload(file!, project, key.current);
      navigate(uploadHref(kept.upload_id));
    } catch (error) {
      const refused = error instanceof ApiError ? (error.body as UploadRefusal & { trace_id?: string }) : null;
      key.current = newKey();
      setPhase({ state: "failed", refusal: refused, name: file!.name, reference: refused?.trace_id ?? null });
    }
  };

  if (phase.state === "reading") {
    return (
      <section className="mt-6 max-w-[640px] rounded-md border border-line bg-surface p-4 @md/page:p-6" data-reading>
        <h2 className="text-title text-ink-heading">{words.heading}</h2>
        <AccessLabel className="mt-2" />
        <p className="mt-3 text-small text-ink">{words.reading}</p>
        <div className="mt-3">
          <Steps reserveLines={2} steps={[
            { key: "upload", running: words.readingSteps.upload(phase.name), done: words.readingSteps.upload(phase.name), state: "running" },
            { key: "check", running: words.readingSteps.check, done: words.readingSteps.check, state: "todo" },
          ]} />
        </div>
      </section>
    );
  }

  const hint = words.format[form.format](words.formats, sizeText(form.limits.max_size_bytes));
  const describedBy = [`${id}-hint`, `${id}-status`, errors.file ? `${id}-file-error` : null].filter(Boolean).join(" ");
  return (
    <>
      {phase.state === "failed" && (
        <div className="mt-6 flex max-w-[640px] flex-col gap-2" data-upload-error={phase.refusal?.code}>
          <Alert state="error" live="alert">
            {phase.refusal ? refusalText(phase.refusal, phase.name) : words.errors.dropped(phase.name)}
          </Alert>
          {phase.refusal?.code === "permission" && <p className="text-body text-ink">{words.permissionBody}</p>}
          {phase.reference && <p className="text-caption text-ink-muted">{words.reference(phase.reference)}</p>}
          {(phase.refusal?.code === "no_table" || phase.refusal?.code === "missing_columns") && <ColumnLists form={form} open headingLevel={2} />}
        </div>
      )}
      <section aria-labelledby={`${id}-heading`} className="mt-6 max-w-[640px] rounded-md border border-line bg-surface p-4 @md/page:p-6" data-upload-card>
        <h2 id={`${id}-heading`} className="text-title text-ink-heading">
          {words.heading}
        </h2>
        <AccessLabel className="mt-2" />
        <p className="mt-3 text-body text-ink">
          {words.privacy(agency)} {words.kept}
        </p>
        <form className="mt-6" onSubmit={submit} noValidate>
          <fieldset disabled={preview} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label htmlFor={`${id}-project`} className="text-small font-bold text-ink-heading">
                {words.projectLabel}
              </label>
              {form.projects.length === 1 ? (
                <p className="text-body text-ink" data-project>
                  <Fill template={copy.breadcrumb.project} slots={{ name: chosen?.display_name ?? chosen?.project_name ?? "", pid: chosen?.project_id ?? "" }} />
                </p>
              ) : (
                <>
                  <p id={`${id}-project-hint`} className="text-caption text-ink-muted">{words.projectHint}</p>
                  <select id={`${id}-project`} ref={projectInput} value={project} onChange={(event) => setProject(event.target.value)}
                    aria-describedby={`${id}-project-hint${errors.project ? ` ${id}-project-error` : ""}`} aria-invalid={Boolean(errors.project) || undefined}
                    className="h-11 rounded-md border border-line-strong bg-surface px-3 text-body text-ink">
                    <option value="">{words.projectPlaceholder}</option>
                    {form.projects.map((one) => (
                      <option key={one.project_id} value={one.project_id}>
                        {words.projectOption(one.display_name ?? one.project_name, one.project_id)}
                      </option>
                    ))}
                  </select>
                  {errors.project && <p id={`${id}-project-error`} className="text-small text-error">{errors.project}</p>}
                </>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor={`${id}-file`} className="text-small font-bold text-ink-heading">
                {words.fileLabel}
              </label>
              <p id={`${id}-hint`} className="text-caption text-ink-muted">{hint}</p>
              <div className={`flex min-h-[68px] flex-wrap items-center gap-3 rounded-md border bg-surface p-3 ${errors.file ? "border-error-icon" : "border-line-strong"}`}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  if (!preview) choose(event.dataTransfer.files[0] ?? null);
                }}
                data-file-field>
                <input id={`${id}-file`} ref={fileInput} type="file" accept={form.limits.accept.join(",")} className="peer sr-only"
                  aria-describedby={describedBy} aria-invalid={Boolean(errors.file) || undefined}
                  onChange={(event) => choose(event.target.files?.[0] ?? null)} />
                <span aria-hidden="true"
                  className="inline-flex h-11 cursor-pointer items-center rounded-pill border-2 border-primary px-6 text-button text-primary peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus"
                  onClick={() => fileInput.current?.click()}>
                  {words.choose}
                </span>
                <span id={`${id}-status`} className="text-small text-ink-muted" data-file-status>
                  {file ? words.chosen(file.name, sizeText(file.size)) : words.none}
                </span>
              </div>
              {errors.file && <p id={`${id}-file-error`} className="text-small text-error" data-file-error>{errors.file}</p>}
              <ColumnLists form={form} />
            </div>
          </fieldset>
          <div className="mt-6 flex flex-col items-start gap-2">
            <Button type="submit" variant="primary" held={preview} aria-describedby={`${id}-feedforward`} data-upload-submit>
              {words.submit}
            </Button>
            <p id={`${id}-feedforward`} className="text-caption text-ink-muted">
              {preview ? words.holdPreview : words.feedforward}
            </p>
          </div>
        </form>
      </section>
      <section className="mt-8 max-w-[72ch]" aria-labelledby={`${id}-published`}>
        <h2 id={`${id}-published`} className="text-title text-ink-heading">{words.publishedHeading}</h2>
        {form.projects.some((one) => one.latest_plan) ? (
          <>
            <p className="mt-2 text-body text-ink">{words.publishedIntro(agency)}</p>
            <ul className="mt-4 flex flex-col gap-3" data-published-plans>
              {form.projects.filter((one) => one.latest_plan).map((one) => (
                <li key={one.project_id}>
                  <TextLink href={`/projects/${one.project_id}/procurement/${one.latest_plan!.agency_id}/${one.latest_plan!.plan_date}`}
                    className="text-body font-semibold">
                    {words.publishedItem(formatDate(one.latest_plan!.plan_date))}
                  </TextLink>
                  <p className="text-caption text-ink-muted">
                    <Fill template={words.publishedCaption} slots={{ name: one.display_name ?? one.project_name, pid: one.project_id,
                      date: one.latest_plan!.disclosed_on ? short(one.latest_plan!.disclosed_on) : "" }} />
                  </p>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="mt-2 text-body text-ink">{words.publishedNone(agency)}</p>
        )}
        {form.earlier > 0 && !preview && (
          <p className="mt-6 text-small text-ink-muted" data-earlier>
            {words.earlier(form.earlier, formatCount(form.earlier))}
          </p>
        )}
      </section>
    </>
  );
}
