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

// Serve /api from recorded responses. An /api call with no recording fails the test that made it.
export async function mockApi(page: Page, responses: Record<string, { status?: number; body: string }>) {
  const unrecorded: string[] = [];
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const response = responses[path];
    if (!response) {
      unrecorded.push(path);
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
