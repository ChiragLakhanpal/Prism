// The setup every screen test shares (seam 4): the network is off, and /api answers from the
// responses recorded in tests/fixtures/api, the same files the server tests check the server against.
import { readFile } from "node:fs/promises";
import { test as base, expect, type Page } from "@playwright/test";

const RECORDED = new URL("../../tests/fixtures/api/", import.meta.url);

export async function recorded(name: string): Promise<string> {
  return readFile(new URL(name, RECORDED), "utf8");
}

type Fixtures = { outsideRequests: string[] };

export const test = base.extend<Fixtures>({
  // In every test, any request that leaves the app's own origin is refused and listed,
  // and the test fails if the list is not empty at the end.
  outsideRequests: [
    async ({ context, baseURL }, use) => {
      const origin = new URL(baseURL!).origin;
      const outside: string[] = [];
      await context.route((url) => url.origin !== origin, (route) => {
        outside.push(route.request().url());
        return route.abort("internetdisconnected");
      });
      await use(outside);
      expect(outside, "the screen tried to reach the network").toEqual([]);
    },
    { auto: true },
  ],
});

// The recording an address answers with. A key may carry a query, such as "/api/projects?q=india&page=2"
// (ticket 21): it matches when the path matches and each of its parameters has that value in the address,
// and the key with the most parameters wins. A key with no query matches its path whatever the query is,
// as every key did before ticket 21, so the tests written then still hold.
export function recordingFor<T>(responses: Record<string, T>, url: URL): T | undefined {
  let best: T | undefined;
  let most = -1;
  for (const [key, response] of Object.entries(responses)) {
    const [path, query = ""] = key.split("?");
    if (path !== url.pathname) continue;
    const params = [...new URLSearchParams(query)];
    if (params.every(([name, value]) => url.searchParams.get(name) === value) && params.length > most) {
      best = response;
      most = params.length;
    }
  }
  return best;
}

// Serve /api from recorded responses. An /api call with no recording fails the test that made it.
export async function mockApi(page: Page, responses: Record<string, { status?: number; body: string }>) {
  const unrecorded: string[] = [];
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    const response = recordingFor(responses, url);
    if (!response) {
      unrecorded.push(url.pathname + url.search);
      return route.fulfill({ status: 404, json: { detail: "Not Found" } });
    }
    return route.fulfill({ status: response.status ?? 200, contentType: "application/json", body: response.body });
  });
  return unrecorded;
}

// The two calls every page of the shell makes, answered from the recordings unless a test says
// otherwise: who is viewing (/api/me) and the data-freshness stamp (/api/freshness).
export async function mockShell(
  page: Page,
  answers: { me?: { status?: number; body: string }; freshness?: { status?: number; body: string } } = {},
) {
  return mockApi(page, {
    "/api/me": answers.me ?? { body: await recorded("me.json") },
    "/api/freshness": answers.freshness ?? { body: await recorded("freshness.json") },
  });
}

export { expect };
