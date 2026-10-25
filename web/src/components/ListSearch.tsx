// List search (DESIGN.md section 5; the 21 brief, section 10): a field that filters a list on the server
// as you type, as All projects and a project's Packages do. A visible label in small 700, a hint in
// caption that the field is described by, and a pill 44 px tall with a 1 px line-strong border, a 16 px
// search icon and, while it holds text, a 32 px ghost x named "Empty the search box". It has no
// placeholder, so the hint never disappears as you type.
//
// It tells the page 250 ms after typing stops (onSearch), so a fast typist sends one request. Escape and
// the x empty it at once, and the x gives focus back to the field. The page owns the query, which lives
// in the address, and the field follows it when it changes from elsewhere, such as "Show all projects".
import { useEffect, useId, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";

export const SEARCH_WAIT_MS = 250;

export function ListSearch({
  label,
  hint,
  value,
  onSearch,
  className,
}: {
  label: string;
  hint: string;
  // The query the page shows rows for.
  value: string;
  onSearch: (query: string) => void;
  className?: string;
}) {
  const inputId = useId();
  const hintId = useId();
  const field = useRef<HTMLInputElement>(null);
  const [text, setText] = useState(value);
  const typed = useRef(value);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // A query set from elsewhere, such as a link that shows every row, empties or fills the field.
  useEffect(() => {
    if (value !== typed.current) {
      typed.current = value;
      setText(value);
    }
  }, [value]);
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const send = (query: string, wait: number) => {
    typed.current = query;
    if (timer.current) clearTimeout(timer.current);
    if (wait === 0) onSearch(query);
    else timer.current = setTimeout(() => onSearch(query), wait);
  };
  const empty = () => {
    setText("");
    send("", 0);
    field.current?.focus();
  };

  return (
    <div className={cx("flex flex-col", className)} data-list-search>
      <label htmlFor={inputId} className="text-small font-bold text-ink-heading">
        {label}
      </label>
      <p id={hintId} className="text-caption text-ink-muted">
        {hint}
      </p>
      <div className="relative mt-2">
        <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-ink-muted" />
        <input
          ref={field}
          id={inputId}
          type="search"
          value={text}
          aria-describedby={hintId}
          autoComplete="off"
          spellCheck={false}
          onChange={(event) => {
            setText(event.target.value);
            send(event.target.value, SEARCH_WAIT_MS);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape" && text) {
              event.preventDefault();
              event.stopPropagation();
              empty();
            }
          }}
          className={cx(
            "h-11 w-full rounded-pill border border-line-strong bg-surface pr-12 pl-10 text-body text-ink",
            "[&::-webkit-search-cancel-button]:appearance-none",
          )}
        />
        {text && (
          <button
            type="button"
            aria-label={copy.listSearch.empty}
            onClick={empty}
            className="absolute top-1/2 right-1.5 flex size-8 -translate-y-1/2 items-center justify-center rounded-pill text-primary hover:bg-tint-hover"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        )}
      </div>
    </div>
  );
}
