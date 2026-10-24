// The words the server writes into the Data readiness page's sentences (copy.dataReadiness.server),
// copied from web/src/copy.ts into src/strata/tools/data_readiness_copy.json, which the
// data_readiness_for tool reads. The copy file stays their one home: the lint lane fails when the
// JSON file is out of date (web/lint/run.ts), and this command writes it again:
//
//     node web/lint/server-copy.ts --write
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { copy } from "../src/copy.ts";

export const SERVER_COPY_FILE = fileURLToPath(new URL("../../src/strata/tools/data_readiness_copy.json", import.meta.url));

export function serverCopy(): string {
  const words = {
    ...copy.dataReadiness.server,
    words: copy.num.words,
    badges: { partial: copy.badge.partial, gap: copy.badge.gap },
    footer: copy.footer,
  };
  return `${JSON.stringify(words, null, 2)}\n`;
}

// Whether the JSON file says what the copy file says.
export function serverCopyIsCurrent(): boolean {
  try {
    return readFileSync(SERVER_COPY_FILE, "utf8") === serverCopy();
  } catch {
    return false;
  }
}

if (process.argv.includes("--write") && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  writeFileSync(SERVER_COPY_FILE, serverCopy());
  console.log(`Wrote ${SERVER_COPY_FILE}.`);
}
