// What a page shows when its read fails (the 10 brief, section 6). A viewer whose account can't read
// Strata's tables gets that sentence and what to ask for, with no retry, because trying again can't
// help. Any other failure gets the page's sentence, "Try again" 16 px below it, and the reference
// that finds the details in the server's log. Each failed try announces the alert again, and the
// button keeps focus.
import { copy } from "../copy";
import type { ApiError } from "../lib/api";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";

export function LoadError({
  error,
  message,
  permission,
  onRetry,
  retrying,
  attempt,
}: {
  error: ApiError | null;
  // The page's own sentence for a service that didn't answer, and for an account that can't read.
  message: string;
  permission: string;
  onRetry: () => void;
  retrying: boolean;
  attempt: number;
}) {
  if (error?.status === 403) {
    return (
      <div data-load-error="permission">
        <Alert state="error" live="alert">
          {permission}
        </Alert>
        <p className="mt-4 max-w-prose text-body text-ink">{copy.service.permissionBody}</p>
      </div>
    );
  }
  const reference = error?.body.trace_id;
  return (
    <div data-load-error="service">
      <Alert key={attempt} state="error" live="alert">
        {message}
      </Alert>
      <Button className="mt-4" variant="secondary" loading={retrying} onClick={onRetry}>
        {copy.answer.tryAgain}
      </Button>
      {reference && (
        <p className="mt-2 text-caption text-ink-muted">
          <Fill template={copy.service.reference} slots={{ reference: <span className="font-mono">{reference}</span> }} />
        </p>
      )}
    </div>
  );
}
