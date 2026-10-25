// Toggle button (DESIGN.md section 5; the 32 brief, section 3.2): a ghost or secondary button with aria-pressed,
// such as "Wrong passage" in the evidence drawer or a grade on the judging page. Pressed, a ghost button takes the
// tint fill and a 2 px primary border; a secondary one takes the tint fill, an inset 2 px primary ring and lucide
// check in its icon slot. The border is always 2 px and the icon slot is always kept, so pressing moves nothing.
// It is never filled with primary, so a pressed toggle never reads as the page's one primary action. Disabled, it
// takes the Held button look: a ghost is a bare ink-muted label, a secondary one a surface-2 pill. A ghost in a column
// of text (inText), such as the drawer's "Wrong passage", has 16 px of padding, so the first of a row can be pulled
// left onto the text's edge while its pressed border and focus ring stay inside the drawer's 24 px padding.
import type { ComponentProps, ReactNode } from "react";
import { Check } from "lucide-react";
import { cx } from "../lib/cx";

export function ToggleButton({
  pressed,
  variant = "ghost",
  disabled = false,
  hint,
  inText = false,
  className,
  children,
  onClick,
  ...rest
}: Omit<ComponentProps<"button">, "disabled"> & {
  pressed: boolean;
  variant?: "ghost" | "secondary";
  // Disabled stays focusable (aria-disabled), described by the sentence that says why.
  disabled?: boolean;
  // A key hint after the label, such as "A" on a grade button (brief 14's key-hint style).
  hint?: ReactNode;
  // A ghost in a column of text: 16 px of padding instead of 24.
  inText?: boolean;
}) {
  return (
    <button
      {...rest}
      type="button"
      aria-pressed={pressed}
      aria-disabled={disabled || undefined}
      data-toggle={variant}
      data-pressed={pressed || undefined}
      onClick={disabled ? (event) => event.preventDefault() : onClick}
      className={cx(
        "relative inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-pill border-2 text-button",
        inText ? "px-4" : "px-6",
        "transition-paint duration-150 select-none motion-reduce:transition-none",
        disabled
          ? variant === "ghost"
            ? "cursor-not-allowed border-transparent bg-transparent text-ink-muted"
            : "cursor-not-allowed border-line bg-surface-2 text-ink-muted"
          : variant === "ghost"
            ? pressed
              ? "border-primary bg-tint text-primary"
              : "border-transparent bg-transparent text-primary hover:bg-tint-hover"
            : pressed
              ? "border-primary bg-tint text-primary shadow-[inset_0_0_0_2px_var(--color-primary)]"
              : "border-primary bg-surface text-primary hover:bg-tint",
        className,
      )}
    >
      {variant === "secondary" && (
        <span aria-hidden="true" className="inline-flex size-4 shrink-0 items-center justify-center">
          {pressed && <Check className="size-4" />}
        </span>
      )}
      <span>{children}</span>
      {hint && <KeyHint>{hint}</KeyHint>}
    </button>
  );
}

// Key hint (DESIGN.md section 5): a 1 px line-strong box, radius 4, caption ink-muted, shown from 768 px on a device
// with hover only. It is aria-hidden: the button carries aria-keyshortcuts, and the keys note says the same.
export function KeyHint({ children }: { children: ReactNode }) {
  return (
    <span
      aria-hidden="true"
      data-key-hint
      className="hidden rounded-sm border border-line-strong px-1 text-caption text-ink-muted md:can-hover:inline"
    >
      {children}
    </span>
  );
}
