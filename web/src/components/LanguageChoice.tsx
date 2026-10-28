// Language choice: "Language of answers and drafts" in the view popover, and at the foot of the Menu panel below
// 1024 px (ticket 42; the 42 design brief, sections 3.5, 4.3 and 5.1; DESIGN.md section 5, Top navigation). It is a
// segmented control of the choice kind, stacked at 44 px: native radios in a fieldset named by its legend and
// described by its hint, so the arrow keys move and choose. Each language shows its English name and, beside it, its
// own name in its own language. The screens stay in English whatever you choose.
//
// A choice takes effect at once, so the box, the draft actions and "Ask again" follow it; 500 ms after the last move
// the server keeps it for next time (PUT /api/me/working-language). When it can't, the choice holds in the page's
// address as ?lang= instead. The status line says what happened, and says where the language came from when a link
// or your team chose it.
import { Check, CircleX } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { choiceNote, chooseLanguage, ENGLISH, languageName, workingLanguage, type WorkingLanguage } from "../lib/lang";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { Skeleton } from "./Skeleton";

const SAVE_AFTER_MS = 500;

async function save(code: string): Promise<boolean> {
  try {
    const response = await fetch("/api/me/working-language", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

// The page's address with ?lang= set to code, or without it, in place.
function keepInAddress(code: string | null) {
  const params = new URLSearchParams(address.get().search);
  if (code) params.set("lang", code);
  else params.delete("lang");
  const rest = params.toString();
  navigate(`${window.location.pathname}${rest ? `?${rest}` : ""}${window.location.hash}`, { replace: true, quiet: true });
}

function statusLine(language: WorkingLanguage, note: ReturnType<typeof choiceNote.get>) {
  const words = copy.language.choice;
  if (note === "changed") return words.changed(languageName(language.code));
  if (note === "saveFailed") return words.saveFailed;
  if (!language.saved_readable) return words.readFailed(languageName(language.code));
  if (language.source === "link" && language.code !== (language.saved ?? ENGLISH)) {
    return words.fromLink(languageName(language.code), languageName(language.saved ?? ENGLISH));
  }
  if (language.source === "team") return words.fromTeam(languageName(language.code));
  return "";
}

export function LanguageChoice({ className }: { className?: string }) {
  const language = useStore(workingLanguage);
  const note = useStore(choiceNote);
  const hint = useId();
  const legend = useId();
  const group = useId();
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const choose = (code: string) => {
    workingLanguage.set((now) => (now ? { ...now, code } : now));
    choiceNote.set(null);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void chooseLanguage(code, save, keepInAddress), SAVE_AFTER_MS);
  };

  return (
    <fieldset data-language-choice aria-describedby={hint} className={cx("min-w-0", className)}>
      <legend id={legend} className="text-small font-semibold text-ink">
        {copy.language.choice.legend}
      </legend>
      <p id={hint} className="mt-1 text-caption text-pretty text-ink-muted">
        {copy.language.choice.hint}
      </p>
      <div className="mt-2 flex flex-col overflow-hidden rounded-md border border-line-strong">
        {language === null
          ? [0, 1, 2, 3].map((row) => (
              <div key={row} className="flex min-h-11 items-center border-t border-line-strong px-3 first:border-t-0">
                <Skeleton className="h-[13px] w-24" />
              </div>
            ))
          : language.choices.map((choice) => {
              const selected = choice.code === language.code;
              return (
                <label
                  key={choice.code}
                  data-language={choice.code}
                  className={cx(
                    "relative flex min-h-11 cursor-pointer items-center gap-2 border-t border-line-strong px-3 first:border-t-0",
                    "has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2 has-[:focus-visible]:outline-focus",
                    selected ? "bg-tint shadow-[inset_0_0_0_2px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
                  )}
                >
                  <input
                    type="radio"
                    name={group}
                    value={choice.code}
                    checked={selected}
                    onChange={() => choose(choice.code)}
                    className="sr-only"
                  />
                  <span className="flex size-4 shrink-0 items-center justify-center">
                    {selected && <Check aria-hidden="true" className="size-4 text-primary" />}
                  </span>
                  <span className="w-[6.5rem] shrink-0 text-small font-semibold text-ink">{languageName(choice.code)}</span>
                  {choice.code !== ENGLISH && (
                    <span lang={choice.code} dir={choice.direction === "rtl" ? "rtl" : undefined} className="text-caption text-ink-muted">
                      {choice.endonym}
                    </span>
                  )}
                </label>
              );
            })}
      </div>
      <p role="status" data-language-status className="mt-2 flex min-h-5 items-start gap-1 text-caption text-pretty text-ink-muted">
        {language && note === "saveFailed" && <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />}
        <span className={note === "saveFailed" ? "text-error" : undefined}>{language ? statusLine(language, note) : ""}</span>
      </p>
    </fieldset>
  );
}
