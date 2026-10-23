// Playwright runs the built app (web/dist) with `vite preview` on a free port, so it never
// clashes with a dev server or with another worktree's tests. Build first: npm run build.
import { defineConfig, devices } from "@playwright/test";
import { freePort } from "./free-port";

// This file loads in the runner and again in each worker. The runner picks the port and
// passes it on through the environment, so every process uses the same one.
process.env.STRATA_TEST_WEB_PORT ||= String(await freePort());
const port = Number(process.env.STRATA_TEST_WEB_PORT);
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "tests",
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: [["line"]],
  use: { baseURL, trace: "off" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npx vite preview --host 127.0.0.1 --port ${port} --strictPort`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
