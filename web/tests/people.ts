// Every person's name and email in both roles files (config/roles.toml and the offline tests' tests/fixtures/roles.toml),
// read from the files themselves, so a check that no page under /lessons prints a person (ticket 140) covers whoever
// the files list now.
import { readFile } from "node:fs/promises";

const FILES = [new URL("../../config/roles.toml", import.meta.url), new URL("../../tests/fixtures/roles.toml", import.meta.url)];

export async function people(): Promise<string[]> {
  const found = new Set<string>();
  for (const file of FILES) {
    const text = await readFile(file, "utf8");
    // Only the [[people]] entries: a team or a group also has a name.
    for (const entry of text.split("[[people]]").slice(1)) {
      for (const key of ["name", "email"]) {
        const value = new RegExp(`^${key} = "([^"]+)"`, "m").exec(entry.split(/^\[/m)[0]);
        if (value) found.add(value[1]);
      }
    }
  }
  return [...found];
}

// Any email address at all.
export const EMAIL = /[\w.%+-]+@[\w-]+\.[\w.]+/;
