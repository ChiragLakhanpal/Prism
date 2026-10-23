// The web app's dev server listens on STRATA_WEB_PORT, or on a free port when it is unset.
// It passes /api on to the server at STRATA_SERVER_HOST and STRATA_SERVER_PORT, the same
// variables the server reads. scripts/dev sets both ports.
//
// The design gallery (web/src/gallery) is built only in development and in the "gallery"
// mode (npm run build:gallery, into dist-gallery). A production build leaves it out, and
// web/tests/build.spec.ts checks that on the build output.
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { freePort } from "./free-port";

const repoRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig(async ({ command, mode }) => {
  const serverPort = process.env.STRATA_SERVER_PORT;
  const serverHost = process.env.STRATA_SERVER_HOST?.trim() || "127.0.0.1";
  const serverUrl = `http://${serverHost.includes(":") ? `[${serverHost}]` : serverHost}:${serverPort}`;
  if (command === "serve" && !serverPort) {
    console.warn("STRATA_SERVER_PORT is not set, so calls to /api reach no server. Start both with scripts/dev.");
  }
  return {
    plugins: [react(), tailwindcss()],
    define: { __GALLERY__: JSON.stringify(mode !== "production") },
    server: {
      host: "127.0.0.1",
      port: Number(process.env.STRATA_WEB_PORT) || (await freePort()),
      strictPort: true,
      proxy: serverPort ? { "/api": serverUrl } : undefined,
      // The copy file reads GLOSSARY.md from the repo root.
      fs: { allow: [repoRoot] },
    },
    preview: { host: "127.0.0.1", strictPort: true },
  };
});
