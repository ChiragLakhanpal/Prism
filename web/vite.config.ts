// The web app's dev server listens on STRATA_WEB_PORT, or on a free port when it is unset.
// It passes /api on to the server at STRATA_SERVER_HOST and STRATA_SERVER_PORT, the same
// variables the server reads. scripts/dev sets both ports.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { freePort } from "./free-port";

export default defineConfig(async ({ command }) => {
  const serverPort = process.env.STRATA_SERVER_PORT;
  const serverHost = process.env.STRATA_SERVER_HOST?.trim() || "127.0.0.1";
  const serverUrl = `http://${serverHost.includes(":") ? `[${serverHost}]` : serverHost}:${serverPort}`;
  if (command === "serve" && !serverPort) {
    console.warn("STRATA_SERVER_PORT is not set, so calls to /api reach no server. Start both with scripts/dev.");
  }
  return {
    plugins: [react()],
    server: {
      host: "127.0.0.1",
      port: Number(process.env.STRATA_WEB_PORT) || (await freePort()),
      strictPort: true,
      proxy: serverPort ? { "/api": serverUrl } : undefined,
    },
    preview: { host: "127.0.0.1", strictPort: true },
  };
});
