// Follow control (DESIGN.md section 5; the 37 brief, section 6): a 44 px row in the project header's flow, under
// the agency line. Not following: a secondary "Follow this project" with a plus icon. Following: the small sentence
// "You follow this project." with a check icon, then a ghost "Unfollow" that the sentence describes. The state says
// itself in words and each button says what it will do, so it is not a pressed toggle.
//
// A press shows the busy label "Saving" in the button at its own width, and the state changes only when the server
// confirms it. Focus then moves to the other state's button and a polite status says what changed. On failure the
// state stays, focus stays on the button, and an error line appears under the row. When reading the state fails, the
// row says so with "Try again" and offers neither button. World Bank staff only: the
// project page leaves the row out for everyone else and in both previews.
import { useEffect, useId, useRef, useState } from "react";
import { Check, CircleX, Plus } from "lucide-react";
import { copy } from "../copy";
import { deleteJson, getJson, putJson } from "../lib/api";
import { Button } from "./Button";
import { Skeleton } from "./Skeleton";

const words = copy.projectFollow;

export function FollowControl({ pid, name, sample }: {
  pid: string;
  name: string | null;
  // For the design gallery: whether you follow it (null while it loads), with no request, and whether it is saving
  // or the last change failed.
  sample?: { following: boolean | null; busy?: boolean; failed?: boolean; unread?: boolean };
}) {
  const start = sample ? (sample.unread ? "unread" : sample.following === null ? "loading" : sample.following ? "on" : "off") : "loading";
  // unread: reading whether you follow it failed, so no button claims a state until it is read again.
  const [state, setState] = useState<"loading" | "off" | "on" | "unread">(start);
  // A follow the seed command made for you (ticket 41): the sentence says Strata made it, until you change it.
  const [example, setExample] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(sample?.busy ?? false);
  const [failed, setFailed] = useState<"on" | "off" | null>(sample?.failed ? (sample.following ? "off" : "on") : null);
  const [said, setSaid] = useState("");
  const sentenceId = useId();
  const focusNext = useRef(false);
  const follow = useRef<HTMLButtonElement>(null);
  const unfollow = useRef<HTMLButtonElement>(null);
  const path = `/api/projects/${encodeURIComponent(pid)}/follow`;

  useEffect(() => {
    if (sample) return;
    const controller = new AbortController();
    getJson<{ following: boolean; example?: boolean }>(path, { signal: controller.signal }).then(
      (answer) => {
        setState(answer.following ? "on" : "off");
        setExample(Boolean(answer.example));
      },
      () => !controller.signal.aborted && setState("unread"),
    );
    return () => controller.abort();
  }, [path, attempt]);

  useEffect(() => {
    if (!focusNext.current) return;
    focusNext.current = false;
    (state === "on" ? unfollow : follow).current?.focus();
  }, [state]);

  const change = async (to: "on" | "off") => {
    if (busy) return;
    setBusy(true);
    setFailed(null);
    try {
      const answer = await (to === "on" ? putJson<{ following: boolean }>(path, {}) : deleteJson<{ following: boolean }>(path));
      focusNext.current = true;
      setExample(false);
      setState(answer.following ? "on" : "off");
      setSaid(answer.following ? words.announceOn(name ?? pid) : words.announceOff(name ?? pid));
    } catch {
      setFailed(to);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4" data-follow={state}>
      <div role="group" aria-label={words.label} aria-busy={busy || undefined} className="flex min-h-11 flex-wrap items-center gap-x-3 gap-y-2">
        {state === "loading" && <Skeleton className="h-11 w-[184px]" radius="rounded-pill" />}
        {state === "unread" && (
          <>
            <p role="alert" className="flex items-start gap-1 text-small text-error" data-follow-unread>
              <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
              {words.unread}
            </p>
            <Button variant="ghost" onPage onClick={() => { setState("loading"); setAttempt(attempt + 1); }}>
              {words.retry}
            </Button>
          </>
        )}
        {state === "off" && (
          <Button ref={follow} variant="secondary" icon={Plus} loading={busy} busyLabel={words.busy} onClick={() => change("on")}>
            {words.button}
          </Button>
        )}
        {state === "on" && (
          <>
            <p id={sentenceId} className="flex items-center gap-1 text-small text-ink">
              <Check aria-hidden="true" className="size-4 text-ink-muted" />
              {example ? copy.home.exampleFollowed : words.state}
            </p>
            <Button ref={unfollow} variant="ghost" onPage loading={busy} busyLabel={words.busy} aria-describedby={sentenceId} onClick={() => change("off")}>
              {words.unfollow}
            </Button>
          </>
        )}
      </div>
      {failed && (
        <p role="alert" className="mt-2 flex items-start gap-1 text-small text-error" data-follow-failed>
          <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
          {failed === "on" ? words.failedOn : words.failedOff}
        </p>
      )}
      <p role="status" className="sr-only">
        {said}
      </p>
    </div>
  );
}
