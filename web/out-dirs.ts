// Where the web builds go, as folders under web/. The app builds into dist and the design gallery
// into dist-gallery. When STRATA_WEB_DIST names another folder, the app builds into that one and the
// gallery into the same name with -gallery after it. The gate's two web lanes each name their own
// folder, so each lane's Playwright run serves its own build while the other lane builds
// (gates/steps.toml). vite.config.ts, both Playwright configs and tests/build.spec.ts read it here.
const named = process.env.STRATA_WEB_DIST?.trim() || "dist";

// Vite empties the folder before each build, so only a dist folder under web/ may be named.
if (!/^dist(-[a-z0-9]+)*$/.test(named)) {
  throw new Error(`STRATA_WEB_DIST must name a folder under web/ that starts with dist, such as dist-1, not "${named}".`);
}

export const appDir = named;
export const galleryDir = `${named}-gallery`;
// Each build folder keeps its own Playwright results and Vite cache, so two runs side by side never
// clean or rewrite each other's.
export const resultsDir = `test-results/${named}`;
export const viteCacheDir = named === "dist" ? "node_modules/.vite" : `node_modules/.vite-${named}`;
