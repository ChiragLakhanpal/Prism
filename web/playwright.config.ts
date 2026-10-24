// Playwright runs the built app (web/dist) with `vite preview` on a free port, so it never
// clashes with a dev server or with another worktree's tests. Build first: npm run build.
// The gallery's tests (tests/gallery*.spec.ts) run against the gallery build (web/dist-gallery,
// from npm run build:gallery) on a second free port; the production build has no gallery.
// tests/dev.spec.ts runs against Vite's dev server on a third free port, as scripts/dev serves the
// app, because React's StrictMode runs every effect twice there and only there (ticket 14).
import { defineConfig, devices } from "@playwright/test";
import { freePort } from "./free-port";

// This file loads in the runner and again in each worker. The runner picks the ports and
// passes them on through the environment, so every process uses the same ones.
process.env.STRATA_TEST_WEB_PORT ||= String(await freePort());
process.env.STRATA_TEST_GALLERY_PORT ||= String(await freePort());
process.env.STRATA_TEST_DEV_PORT ||= String(await freePort());
const port = Number(process.env.STRATA_TEST_WEB_PORT);
const galleryPort = Number(process.env.STRATA_TEST_GALLERY_PORT);
const baseURL = `http://127.0.0.1:${port}`;
const galleryURL = `http://127.0.0.1:${galleryPort}`;
const devPort = Number(process.env.STRATA_TEST_DEV_PORT);
const devURL = `http://127.0.0.1:${devPort}`;
const GALLERY_TESTS = /gallery.*\.spec\.ts$/;
const DEV_TESTS = /dev\.spec\.ts$/;

export default defineConfig({
  testDir: "tests",
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: [["line"]],
  use: { trace: "off" },
  projects: [
    { name: "app", testIgnore: [GALLERY_TESTS, DEV_TESTS], use: { ...devices["Desktop Chrome"], baseURL } },
    { name: "gallery", testMatch: GALLERY_TESTS, use: { ...devices["Desktop Chrome"], baseURL: galleryURL } },
    { name: "dev", testMatch: DEV_TESTS, use: { ...devices["Desktop Chrome"], baseURL: devURL } },
  ],
  webServer: [
    {
      command: `npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
      url: baseURL,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `npx vite preview --host 127.0.0.1 --port ${galleryPort} --strictPort --outDir dist-gallery`,
      url: galleryURL,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // No STRATA_SERVER_PORT, so the dev server passes /api nowhere; the tests answer it.
      command: `npx vite --host 127.0.0.1 --port ${devPort} --strictPort --clearScreen false --logLevel warn`,
      url: devURL,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
