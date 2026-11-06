// Field photos on the Deep research tab (ticket 150): the photos the viewer's team took on a mission, each with the
// date its camera recorded and the project location nearest where it was taken, labelled Official Use Only and visible
// to the team alone. A World Bank staff viewer adds one with a caption; "Uploading never submits anything" sits beside
// the control (DESIGN.md section 7, rule 39). A run the team starts then cites each photo by its caption and date.
import { useId, useState, type FormEvent } from "react";
import { AccessLabel } from "../../components/AccessLabel";
import { Alert } from "../../components/Alert";
import { Button } from "../../components/Button";
import { ExternalLink } from "../../components/ExternalLink";
import { copy } from "../../copy";
import { ApiError } from "../../lib/api";
import { fieldPhotosPath, sendFieldPhoto, type FieldPhoto, type FieldPhotoList } from "../../lib/fieldPhotos";
import { formatCount, formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { useStore } from "../../lib/store";
import { address } from "../../lib/router";
import { withReadParams } from "../../lib/view";

const words = copy.research.photos;

function where(photo: FieldPhoto): string {
  if (photo.place) return words.near(photo.place);
  if (photo.latitude !== null && photo.longitude !== null) return words.position(photo.latitude.toFixed(4), photo.longitude.toFixed(4));
  return words.noPlace;
}

function refusal(error: unknown, list: FieldPhotoList): string {
  const code = error instanceof ApiError ? (error.body as { code?: string }).code : undefined;
  if (code === "size") return words.errors.size(formatCount(Math.round(list.limits.max_size_bytes / 1_048_576)));
  if (code === "count") return words.errors.count(formatCount(list.limits.max_per_project));
  if (code === "format" || code === "caption" || code === "not_staff") return words.errors[code];
  return words.errors.service;
}

export function FieldPhotos({ pid }: { pid: string }) {
  const search = useStore(address).search;
  const [reads, setReads] = useState(0);
  const [load] = useLoad<FieldPhotoList>(withReadParams(fieldPhotosPath(pid), search), String(reads));
  const [file, setFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [state, setState] = useState<{ phase: "idle" | "adding" | "added" | "refused"; message?: string }>({ phase: "idle" });
  const id = useId();

  if (load.status === "loading") return null;
  if (load.status === "error") {
    return (
      <section data-field-photos="error" className="mt-10 max-w-prose">
        <h2 className="text-h2 text-ink-heading">{words.heading}</h2>
        <p className="mt-2 text-small text-ink-muted">{words.loadError}</p>
      </section>
    );
  }
  const list = load.data;
  if (list.preview) return null;

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) return setState({ phase: "refused", message: words.errors.choose });
    if (!caption.trim()) return setState({ phase: "refused", message: words.errors.caption });
    setState({ phase: "adding" });
    try {
      await sendFieldPhoto(pid, file, caption.trim());
      setFile(null);
      setCaption("");
      setState({ phase: "added", message: words.added });
      setReads((count) => count + 1);
    } catch (error) {
      setState({ phase: "refused", message: refusal(error, list) });
    }
  };

  return (
    <section data-field-photos="ready" aria-labelledby={`${id}-heading`} className="mt-10 max-w-prose">
      <h2 id={`${id}-heading`} className="text-h2 text-ink-heading">
        {words.heading}
      </h2>
      <AccessLabel className="mt-2" />
      <p className="mt-2 text-body text-ink">{words.about}</p>
      {list.photos.length === 0 ? (
        <p className="mt-3 text-small text-ink-muted" data-field-photos-none>
          {words.none}
        </p>
      ) : (
        <ul className="mt-3 flex flex-col gap-3 border-t border-line">
          {list.photos.map((photo) => (
            <li key={photo.photo_id} data-field-photo={photo.photo_id} className="flex flex-col gap-1 border-b border-line py-3">
              {/* The photo itself, which the photo route gives the team alone (ticket 156: a picture in every section). */}
              <img src={photo.url} alt="" className="mb-2 block aspect-[4/3] w-full max-w-sm rounded-sm border border-line bg-surface-2 object-cover" />
              <p className="text-body text-ink">{photo.caption}</p>
              <p className="text-small text-ink-muted">
                <span data-field-photo-date>{photo.taken_on ? words.taken(formatDate(photo.taken_on)) : words.noDate}</span>
                {". "}
                <span data-field-photo-place>{where(photo)}</span>
                {". "}
                {photo.uploader.you ? words.addedByYou : words.addedBy(photo.uploader.name ?? "")}
                {". "}
                <ExternalLink href={photo.url} name={`, ${photo.file_name}`}>
                  {words.open}
                </ExternalLink>
              </p>
            </li>
          ))}
        </ul>
      )}
      {list.may_add && (
        <form className="mt-4 flex flex-col gap-3" onSubmit={(event) => void add(event)} data-field-photo-form>
          <label htmlFor={`${id}-file`} className="text-small font-semibold text-ink-heading">
            {words.fileLabel}
          </label>
          <input
            id={`${id}-file`}
            type="file"
            accept={list.limits.accept.join(",")}
            className="text-small text-ink"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <label htmlFor={`${id}-caption`} className="text-small font-semibold text-ink-heading">
            {words.captionLabel}
          </label>
          <p id={`${id}-hint`} className="text-caption text-ink-muted">
            {words.captionHint}
          </p>
          <textarea
            id={`${id}-caption`}
            aria-describedby={`${id}-hint`}
            value={caption}
            maxLength={list.limits.max_caption}
            rows={3}
            className="rounded-sm border border-line-strong bg-surface px-3 py-2 text-body text-ink"
            onChange={(event) => setCaption(event.target.value)}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="secondary" type="submit" disabled={state.phase === "adding"}>
              {words.add}
            </Button>
            <p className="text-small text-ink-muted" data-never-submits>
              {words.neverSubmits}
            </p>
          </div>
          <div aria-live="polite">
            {state.phase === "adding" && <p className="text-small text-ink-muted">{words.adding}</p>}
            {state.phase === "added" && <p className="text-small text-ink" data-field-photo-added>{state.message}</p>}
          </div>
          {state.phase === "refused" && (
            <Alert state="error" live="alert">
              {state.message}
            </Alert>
          )}
        </form>
      )}
    </section>
  );
}
