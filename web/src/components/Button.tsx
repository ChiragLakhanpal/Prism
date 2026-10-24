// Buttons (DESIGN.md section 5): a pill with a 2 px border and 14 px bold text, 44 px tall.
// Primary is the one solid button on a screen; secondary is outlined; ghost is text only.
// Buttons act; links navigate (use TextLink for those).
import type { ComponentProps, ReactNode } from "react";
import { LoaderCircle, type LucideIcon } from "lucide-react";
import { cx } from "../lib/cx";

export type ButtonVariant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "border-primary bg-primary text-surface hover:border-primary-hover hover:bg-primary-hover " +
    "active:border-primary-pressed active:bg-primary-pressed",
  secondary:
    "border-primary bg-surface text-primary hover:bg-tint active:border-primary-pressed active:bg-tint active:text-primary-pressed",
  // Its hover fill is added below: tint-hover on a surface, tint on the page background.
  ghost: "border-transparent bg-transparent text-primary active:bg-tint active:text-primary-pressed",
};

// Disabled: ink-muted text, which is 5.67:1 on surface-2 and 6.69:1 on surface. Primary and
// secondary turn into a surface-2 pill with a line border; ghost stays a bare label, so no
// button changes its shape when it is disabled.
const DISABLED: Record<ButtonVariant, string> = {
  primary:
    "data-disabled:cursor-not-allowed data-disabled:border-line data-disabled:bg-surface-2 data-disabled:text-ink-muted " +
    "data-disabled:hover:border-line data-disabled:hover:bg-surface-2",
  secondary:
    "data-disabled:cursor-not-allowed data-disabled:border-line data-disabled:bg-surface-2 data-disabled:text-ink-muted " +
    "data-disabled:hover:border-line data-disabled:hover:bg-surface-2",
  ghost: "data-disabled:cursor-not-allowed data-disabled:text-ink-muted data-disabled:hover:bg-transparent",
};

// Held (DESIGN.md section 5, Held button; the 35 brief, section 4.3): a button that cannot act yet, such
// as Export to Word before the notes are checked. It stays in its place, so you can see what comes
// next, and stays focusable, described by the visible sentence that says what releases it.
// surface-2 fill and border, ink-muted text (5.67:1), no hover. A held ghost stays a bare label in
// ink-muted, as a disabled one does, so no button changes its shape.
const HELD =
  "cursor-not-allowed border-surface-2 bg-surface-2 text-ink-muted hover:border-surface-2 hover:bg-surface-2 " +
  "active:border-surface-2 active:bg-surface-2 active:text-ink-muted";
const HELD_GHOST =
  "cursor-not-allowed border-transparent bg-transparent text-ink-muted hover:bg-transparent active:bg-transparent " +
  "active:text-ink-muted";

export type ButtonProps = Omit<ComponentProps<"button">, "disabled"> & {
  variant?: ButtonVariant;
  icon?: LucideIcon;
  // Disabled buttons stay focusable, so a keyboard user can still find them and read why.
  disabled?: boolean;
  // Held: it cannot act until something lifts the hold, which its aria-describedby names.
  held?: boolean;
  // While loading, every variant keeps its label and shows a spinner where its icon goes. A
  // button with no icon gives up 12 px of padding on each side for the spinner and its gap,
  // so it stays the same width.
  loading?: boolean;
  // What it says while loading, such as "Saving", in place of its label. Both labels hold one
  // place, so the button keeps the width of the wider one and nothing moves.
  busyLabel?: ReactNode;
  // An icon-only button needs an aria-label from the copy file.
  iconOnly?: boolean;
  // A ghost button in a column of text, such as the answer's "Show the steps I took": 8 px of
  // padding instead of 24 and no side border, pulled left by the same 8 px, so its icon starts
  // on the text's edge above and its label on the edge of the steps list below (Steps indents
  // its text 24 px, the icon and its gap). A ghost's border is clear, so dropping its sides
  // changes nothing you see. Its hover fill then reaches 8 px past the text and its focus ring
  // 12 px, inside the 16 px padding of the smallest card. A flush button carries an icon, so
  // its spinner takes the icon's place and loading does not change its width.
  flush?: boolean;
  // A ghost button on the page background, such as "Show them" in the plan check's fold row:
  // tint-hover barely shows on page, so it hovers to tint.
  onPage?: boolean;
};

export function Button({
  variant = "secondary",
  icon: Icon,
  disabled = false,
  held = false,
  loading = false,
  busyLabel,
  iconOnly = false,
  flush = false,
  onPage = false,
  className,
  children,
  onClick,
  type = "button",
  ...rest
}: ButtonProps) {
  const inactive = disabled || held || loading;
  return (
    <button
      {...rest}
      type={type}
      data-button={variant}
      aria-disabled={inactive || undefined}
      aria-busy={loading || undefined}
      data-disabled={disabled || undefined}
      data-held={held || undefined}
      onClick={inactive ? (event) => event.preventDefault() : onClick}
      className={cx(
        "relative inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-pill border-2 text-button",
        "transition-paint duration-150 select-none",
        iconOnly ? "w-11" : flush ? "-ml-2 border-x-0 px-2" : loading && !Icon ? "px-3" : "px-6",
        held ? (variant === "ghost" ? HELD_GHOST : HELD) : VARIANTS[variant],
        !held && variant === "ghost" && (onPage ? "hover:bg-tint" : "hover:bg-tint-hover"),
        DISABLED[variant],
        loading && "cursor-progress",
        className,
      )}
    >
      {loading ? (
        <LoaderCircle aria-hidden="true" className="size-4 shrink-0 animate-spin" />
      ) : (
        Icon && <Icon aria-hidden="true" className="size-4 shrink-0" />
      )}
      {busyLabel ? (
        // Both labels in one grid cell: the one not showing is invisible, so it keeps its width and
        // a screen reader hears only the one that shows. A flush button's label starts on the text's
        // edge, so it sits at the start of the cell instead of in its middle.
        <span className={cx("grid", flush && "justify-items-start", iconOnly && "sr-only")}>
          <span className={cx("col-start-1 row-start-1", loading && "invisible")}>{children}</span>
          <span className={cx("col-start-1 row-start-1", !loading && "invisible")}>{busyLabel}</span>
        </span>
      ) : (
        <span className={cx(iconOnly && "sr-only")}>{children}</span>
      )}
    </button>
  );
}
