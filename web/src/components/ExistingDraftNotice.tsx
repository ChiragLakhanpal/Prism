// The package workspace's notices about suggested PPSD rows (ticket 36; the 36 brief, section 5.1), in brief 06's
// alert slot above the h1: "I stopped writing ..." once after Stop writing, and the open draft your team already
// started for this package, newest first, with a link to it. The action still offers a new draft.
import { useEffect, useState, type ReactNode } from "react";
import { copy } from "../copy";
import { getJson } from "../lib/api";
import { draftHref, stopped, type ExistingDraft } from "../lib/drafts";
import { formatDate } from "../lib/format";
import { Alert } from "./Alert";
import { TextLink } from "./TextLink";

const words = copy.packageWorkspace.ppsdAction;

export function ExistingPpsdNotice({ packageKey }: { packageKey: string }) {
  const [existing, setExisting] = useState<ExistingDraft | null>(null);
  // Read once, then cleared, so the notice shows on this visit only.
  const [stoppedHere] = useState(() => {
    const at = stopped.get();
    return at !== null && at.startsWith("/packages/");
  });
  useEffect(() => {
    if (stoppedHere) stopped.set(null);
  }, [stoppedHere]);
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ kind: "ppsd_rows", package: packageKey });
    getJson<{ draft: ExistingDraft | null }>(`/api/drafts/existing?${query.toString()}`, { signal: controller.signal }).then(
      (found) => setExisting(found.draft),
      () => undefined,
    );
    return () => controller.abort();
  }, [packageKey]);
  const notices: ReactNode[] = [];
  if (stoppedHere) notices.push(<Alert key="stopped" state="info" live="status">{words.stopped}</Alert>);
  if (existing) {
    const date = formatDate(existing.created_at.slice(0, 10));
    notices.push(
      <Alert key="existing" state="info" action={<TextLink href={draftHref(existing.draft_id)}>{words.existingLink}</TextLink>}>
        <span data-existing-ppsd>{existing.author.you ? words.existingYou(date) : words.existingTeammate(existing.author.name ?? "", date)}</span>
      </Alert>,
    );
  }
  if (notices.length === 0) return null;
  return <div className="mt-4 flex max-w-[72ch] flex-col gap-2">{notices}</div>;
}
