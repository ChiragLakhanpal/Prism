// What a page shows when its read fails (the 10 brief, section 6). A viewer whose account can't read
// Strata's tables gets that sentence and what to ask for, with no retry, because trying again can't
// help. Any other failure gets one alert block: the page's sentence, "Try again" under it and the
// reference that finds the details in the server's log, inside the alert, as the shell redesign's plan
// (8.5), the prototype and the gallery draw it (ticket 60). Each failed try announces the alert again,
// and the button keeps focus.
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
      <Alert
        state="error"
        live="alert"
        action={
          <>
            <Button variant="secondary" loading={retrying} onClick={onRetry}>
              {copy.answer.tryAgain}
            </Button>
            {reference && (
              <p className="mt-2 text-caption text-ink-muted" data-load-error-reference>
                <Fill template={copy.service.reference} slots={{ reference: <span className="font-mono wrap-anywhere">{reference}</span> }} />
              </p>
            )}
          </>
        }
      >
        {/* Only the sentence is keyed by the try, so each failure is announced again while the button stays
            mounted and keeps focus (ticket 60's review, B1). */}
        <span key={attempt}>{message}</span>
      </Alert>
    </div>
  );
}
