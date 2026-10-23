// Calls to Strata's server. Paths start with /api; in development Vite passes them on to the
// server, and in the Databricks App the server serves them itself. Each call carries the
// viewer's session through the App's proxy, so nothing here holds a token.

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly path: string,
  ) {
    super(`${path} answered HTTP ${status}.`);
  }
}

async function call<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { Accept: "application/json", ...init.headers } });
  if (!response.ok) throw new ApiError(response.status, path);
  return (await response.json()) as T;
}

export function getJson<T>(path: string, init: { signal?: AbortSignal } = {}): Promise<T> {
  return call<T>(path, { method: "GET", signal: init.signal });
}

export function postJson<T>(path: string, body: unknown, init: { signal?: AbortSignal } = {}): Promise<T> {
  return call<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: init.signal,
  });
}

// GET /api/me: who the Databricks App says is viewing. The token never leaves the server.
export type Me = { email: string | null; name: string | null; signed_in: boolean; has_token: boolean };
