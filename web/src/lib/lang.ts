// The language of answers and drafts (ticket 42; the 42 design brief, section 6). The server decides which language is
// in effect, from the page's ?lang=, the viewer's saved choice, their team's working language and English, and says
// where it came from (GET /api/me); this store keeps its answer, and every question and draft the page starts takes
// its code. The screens stay in English whatever it is: the copy file is never translated.
import { copy } from "../copy";
import { createStore } from "./store";

export type LanguageChoice = { code: string; endonym: string; direction: string };

export type WorkingLanguage = {
  code: string;
  source: "link" | "saved" | "team" | "default";
  saved: string | null;
  team: string | null;
  // What the link's ?lang= asked for: its language, "unknown" for a value I can't use, or null without one.
  link: string | null;
  saved_readable: boolean;
  choices: LanguageChoice[];
};

export const ENGLISH = "en";

// null until /api/me has answered; then the language in effect. A choice made in the view popover changes it at once.
export const workingLanguage = createStore<WorkingLanguage | null>(null);

// What the language group says after a change or about a link, a team or a failure (the brief, section 5.1).
export type ChoiceNote = "changed" | "saveFailed" | null;
export const choiceNote = createStore<ChoiceNote>(null);

// The code questions and drafts take now: the store's, or English before the server has answered.
export function currentLanguage(): string {
  return workingLanguage.get()?.code ?? ENGLISH;
}

// A language's English name from the copy file ("French"), or its code for a language the copy file does not name.
export function languageName(code: string | null | undefined): string {
  return (code && copy.language.name[code]) || code || copy.language.name[ENGLISH];
}

// The lang attribute an element needs inside text in another language: its own code when the two differ, or nothing.
export function langOf(code: string | null | undefined, around: string = ENGLISH): string | undefined {
  return code && code !== around ? code : undefined;
}

// Choose a language: it takes effect at once, and the server keeps it for next time (PUT /api/me/working-language).
// When the save fails, the choice holds in the page's address as ?lang= instead, so it lasts while you move around.
export async function chooseLanguage(code: string, save: (code: string) => Promise<boolean>, keepInAddress: (code: string | null) => void) {
  workingLanguage.set((now) => (now ? { ...now, code, source: "saved", saved: code, link: null } : now));
  const saved = await save(code);
  keepInAddress(saved ? null : code);
  choiceNote.set(saved ? "changed" : "saveFailed");
}
