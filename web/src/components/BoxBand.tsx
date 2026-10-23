// The white band under the navy bar (DESIGN.md section 5): the one box, which "/" focuses from
// anywhere outside a text field, and the data-freshness stamp. From 768 px the box spans
// columns 1 to 8 and the stamp columns 9 to 12, right-aligned; below that the stamp sits
// under the box. Fixed slots keep the band from moving while the stamp loads.
//
// What Enter does belongs to the tickets that add intents; the box shows their list, or a
// status line, in the `below` slot under it, laid over the page so the band never grows.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { CircleX, Search } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { DOTTED_UNDERLINE } from "./Popover";
import { Skeleton } from "./Skeleton";

function typingInAField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

export function OneBox({
  value,
  onChange,
  below,
  onEscape,
  shortcut = true,
}: {
  // Only the band's box answers "/"; a second box, such as a gallery sample, sets false.
  shortcut?: boolean;
  value: string;
  onChange: (value: string) => void;
  // The status line or the list of what Enter will do, shown while the box has text.
  below?: ReactNode;
  // Escape: the first press closes what is below the box, the second clears the text.
  onEscape?: () => boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const belowId = useId();
  const inputId = useId();
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!shortcut) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey || typingInAField(event.target)) return;
      event.preventDefault();
      input.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [shortcut]);

  const showBelow = Boolean(below) && value.length > 0;
  return (
    <form role="search" className="relative" onSubmit={(event) => event.preventDefault()}>
      <label htmlFor={inputId} className="sr-only">
        {copy.box.label}
      </label>
      <div
        data-focus-ring
        className={cx(
          "flex h-11 items-center gap-2 rounded-pill border border-line-strong bg-surface px-4 transition-paint duration-150",
          "hover:border-ink has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2",
          "has-[input:focus-visible]:outline-focus has-[input:focus-visible]:outline-solid",
        )}
      >
        <Search aria-hidden="true" className="size-4 shrink-0 text-ink-muted" />
        <div className="relative min-w-0 flex-1">
          <input
            ref={input}
            id={inputId}
            type="text"
            value={value}
            placeholder=" "
            autoComplete="off"
            aria-keyshortcuts={shortcut ? "/" : undefined}
            aria-describedby={showBelow ? belowId : undefined}
            onChange={(event) => onChange(event.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={(event) => {
              if (event.key !== "Escape") return;
              if (onEscape?.()) return;
              onChange("");
            }}
            className="peer h-10 w-full bg-transparent text-body text-ink focus-visible:outline-none"
          />
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 hidden items-center truncate text-body text-ink-muted peer-placeholder-shown:flex"
          >
            <span className="truncate min-[30rem]:hidden">{copy.box.placeholderNarrow}</span>
            <span className="hidden truncate min-[30rem]:inline lg:hidden">{copy.box.placeholderMedium}</span>
            <span className="hidden truncate lg:inline">{copy.box.placeholderWide}</span>
          </span>
        </div>
        <kbd
          aria-hidden="true"
          className={cx(
            "hidden shrink-0 rounded-sm border border-line-strong px-1 font-mono text-caption text-ink-muted",
            !focused && value.length === 0 && "lg:inline",
          )}
        >
          /
        </kbd>
      </div>
      {showBelow && (
        <div
          id={belowId}
          role="status"
          className="animate-fade-in absolute inset-x-0 top-full z-40 mt-1 rounded-md border border-line bg-surface p-3 text-small text-ink shadow-popover"
        >
          {below}
        </div>
      )}
    </form>
  );
}

export type Freshness =
  | { status: "loading"; slow?: boolean }
  | { status: "ready"; date: string }
  | { status: "empty" }
  | { status: "error" };

// The data-freshness stamp: caption text, a link to the Data page with a dotted underline
// (the mark of a value you can check), and five honest states. It is not a live region.
export function FreshnessStamp({ freshness, href = "/data" }: { freshness: Freshness; href?: string }) {
  const descriptionId = useId();
  const link = (text: string) => (
    <>
      <a
        href={href}
        aria-describedby={descriptionId}
        className={cx("inline-flex min-h-6 items-center text-caption text-ink-muted tabular-nums hover:text-link-hover", DOTTED_UNDERLINE)}
      >
        {text}
      </a>
      <span id={descriptionId} className="sr-only">
        {copy.stamp.description}
      </span>
    </>
  );
  let body: ReactNode;
  if (freshness.status === "loading") {
    body = freshness.slow ? (
      <span className="text-caption text-ink-muted">{copy.stamp.loading}</span>
    ) : (
      <Skeleton className="h-[13px] w-[124px]" />
    );
  } else if (freshness.status === "ready") body = link(copy.stamp.ready(freshness.date));
  else if (freshness.status === "empty") body = link(copy.stamp.empty);
  else
    body = (
      <span className="inline-flex items-center gap-1 text-caption text-ink-muted">
        <CircleX aria-hidden="true" className="size-4 shrink-0 text-error-icon" />
        {copy.stamp.error}
      </span>
    );
  return (
    <div data-stamp aria-busy={freshness.status === "loading" || undefined} className="flex min-h-6 items-center md:justify-end">
      {body}
    </div>
  );
}

export function BoxBand({ box, stamp }: { box: ReactNode; stamp?: ReactNode }) {
  return (
    <div data-box-band className="border-b border-line bg-surface">
      <div className="layout layout-grid min-h-[68px] items-center gap-y-2 py-3">
        <div className="col-span-12 md:col-span-8">{box}</div>
        <div className="col-span-12 md:col-span-4">{stamp}</div>
      </div>
    </div>
  );
}
