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

// The routes the server tags as calling a model (src/strata/server/tags.py), recorded from its router in
// model-routes.json, which tests/test_project_hub.py keeps in step with create_app. The answer says whether a request
// goes to one of them: a part of a route's path in braces, such as {draft_id}, matches any one part of the address.
export async function modelRoutes(): Promise<{ count: number; callsAModel: (method: string, path: string) => boolean }> {
  const models: { method: string; path: string }[] = JSON.parse(await recorded("model-routes.json")).routes;
  const routes = models.map(({ method, path }) => new RegExp(`^${method} ${path.replace(/\{[^}]+\}/g, "[^/]+")}$`));
  return { count: routes.length, callsAModel: (method, path) => routes.some((route) => route.test(`${method} ${path}`)) };
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

// Who is viewing when the address asks for a preview or a past date (ticket 40): the server's own answers for Ana,
// World Bank staff, recorded by tests/record_views_api.py. A spec that mocks /api/me by its path alone adds these, so
// a page opened with ?view=piu or ?view=public gets the preview the server applies.
export async function viewAnswers(): Promise<Record<string, { body: string }>> {
  const answers: Record<string, { body: string }> = {
    "/api/me?view=piu": { body: await recorded("me-preview-piu.json") },
    "/api/me?view=public": { body: await recorded("me-preview-public.json") },
    "/api/me?asof=2016-08-26": { body: await recorded("me-asof.json") },
    "/api/me?view=public&asof=2016-08-26": { body: await recorded("me-preview-public-asof.json") },
    // Home in each preview, and as of a past date (ticket 41; tests/record_home_api.py).
    "/api/home?view=piu": { body: await recorded("home-preview-piu.json") },
    "/api/home?view=public": { body: await recorded("home-preview-public.json") },
    "/api/home?asof=2016-08-26": { body: await recorded("home-asof-2016-08-26.json") },
    "/api/home?view=public&asof=2016-08-26": { body: await recorded("home-preview-public-2016-08-26.json") },
  };
  return { ...answers, ...Object.fromEntries(Object.entries(answers).map(([key, value]) => [`GET ${key}`, value])) };
}

// The two calls every page of the shell makes, answered from the recordings unless a test says
// otherwise: who is viewing (/api/me) and the data-freshness stamp (/api/freshness). Home's one read (/api/home,
// ticket 41) is answered too, since the shell's tests start there: Ana's Home with her seeded examples.
export async function mockShell(
  page: Page,
  answers: { me?: { status?: number; body: string }; freshness?: { status?: number; body: string }; home?: { status?: number; body: string } } = {},
) {
  return mockApi(page, {
    ...(answers.me ? {} : await viewAnswers()),
    "/api/me": answers.me ?? { body: await recorded("me.json") },
    "/api/freshness": answers.freshness ?? { body: await recorded("freshness.json") },
    "/api/home": answers.home ?? { body: await recorded("home.json") },
  });
}

// Ticket 92: from 1024 px the sidebar sits beside the page, so a page lays out by the window less the sidebar. Ticket
// 110: with no stored choice it rests as the 64 px rail at every width from 1024 px. A test written for a page area of
// a given width opens this window; below 1024 px there is no sidebar, and the window is the page area.
export function windowBeside(area: number): number {
  return area < 1024 ? area : area + 64;
}

// The sidebar as a person leaves it after pressing "Expand the sidebar": open at 224 px from 1024 px, kept in local
// storage under strata.sidebar, which web/index.html reads before the first paint (ticket 110). Call it before goto.
export async function openSidebar(page: Page) {
  await page.addInitScript(() => window.localStorage.setItem("strata.sidebar", "open"));
}

export { expect };
