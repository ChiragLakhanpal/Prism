// One /api read for a page: loading (slow after two seconds), ready, or failed. Trying again keeps
// the failure on screen while the read runs, so the "Try again" button keeps focus; a read that
// works after a retry says so, and the page moves focus to its finding.
import { useCallback, useEffect, useState } from "react";
import { ApiError, getJson } from "./api";

export type Load<T> =
  | { status: "loading"; slow: boolean }
  | { status: "ready"; data: T; afterRetry: boolean }
  | { status: "error"; error: ApiError | null; retrying: boolean; attempt: number };

export const SLOW_AFTER_MS = 2000;

export function useLoad<T>(path: string): [Load<T>, () => void] {
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<Load<T>>({ status: "loading", slow: false });

  useEffect(() => {
    setAttempt(0);
    setLoad({ status: "loading", slow: false });
  }, [path]);

  useEffect(() => {
    const controller = new AbortController();
    const slow = setTimeout(
      () => setLoad((current) => (current.status === "loading" ? { status: "loading", slow: true } : current)),
      SLOW_AFTER_MS,
    );
    getJson<T>(path, { signal: controller.signal }).then(
      (data) => setLoad({ status: "ready", data, afterRetry: attempt > 0 }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setLoad({ status: "error", error: error instanceof ApiError ? error : null, retrying: false, attempt });
      },
    );
    return () => {
      controller.abort();
      clearTimeout(slow);
    };
  }, [path, attempt]);

  const retry = useCallback(() => {
    setLoad((current) => (current.status === "error" ? { ...current, retrying: true } : current));
    setAttempt((count) => count + 1);
  }, []);
  return [load, retry];
}
