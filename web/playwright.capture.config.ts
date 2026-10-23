// The capture command's Playwright setup (npm --prefix web run capture). It is not a gate
// step: it takes a few hundred screenshots, which would break the gate's two-minute limit.
// It serves the production build and the gallery build on free ports, like the tests do.
import { defineConfig, devices } from "@playwright/test";
import { freePort } from "./free-port";

process.env.STRATA_TEST_WEB_PORT ||= String(await freePort());
process.env.STRATA_TEST_GALLERY_PORT ||= String(await freePort());
const appURL = `http://127.0.0.1:${process.env.STRATA_TEST_WEB_PORT}`;
const galleryURL = `http://127.0.0.1:${process.env.STRATA_TEST_GALLERY_PORT}`;
process.env.STRATA_CAPTURE_APP_URL = appURL;
process.env.STRATA_CAPTURE_GALLERY_URL = galleryURL;

export default defineConfig({
  testDir: "capture",
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  reporter: [["line"]],
  use: { ...devices["Desktop Chrome"], trace: "off" },
  webServer: [
    {
      command: `npx vite preview --host 127.0.0.1 --port ${process.env.STRATA_TEST_WEB_PORT} --strictPort`,
      url: appURL,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `npx vite preview --host 127.0.0.1 --port ${process.env.STRATA_TEST_GALLERY_PORT} --strictPort --outDir dist-gallery`,
      url: galleryURL,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
