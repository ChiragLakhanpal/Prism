// Buttons (DESIGN.md section 5): a pill with a 2 px border and 14 px bold text, 44 px tall.
// Primary is the one solid button on a screen; secondary is outlined; ghost is text only.
// Buttons act; links navigate (use TextLink for those).
import type { ComponentProps } from "react";
import { LoaderCircle, type LucideIcon } from "lucide-react";
import { cx } from "../lib/cx";

export type ButtonVariant = "primary" | "secondary" | "ghost";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "border-primary bg-primary text-surface hover:border-primary-hover hover:bg-primary-hover " +
    "active:border-primary-pressed active:bg-primary-pressed",
  secondary:
    "border-primary bg-surface text-primary hover:bg-tint active:border-primary-pressed active:bg-tint active:text-primary-pressed",
  ghost: "border-transparent bg-transparent text-primary hover:bg-tint-hover active:bg-tint active:text-primary-pressed",
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

export type ButtonProps = Omit<ComponentProps<"button">, "disabled"> & {
  variant?: ButtonVariant;
  icon?: LucideIcon;
  // Disabled buttons stay focusable, so a keyboard user can still find them and read why.
  disabled?: boolean;
  // While loading, every variant keeps its label and shows a spinner where its icon goes. A
  // button with no icon gives up 12 px of padding on each side for the spinner and its gap,
  // so it stays the same width.
  loading?: boolean;
  // An icon-only button needs an aria-label from the copy file.
  iconOnly?: boolean;
  // A ghost button in a column of text, such as the answer's "Show the steps I took": 8 px of
  // padding instead of 24, pulled left by the same 8 px, so its icon lines up with the text
  // above. Its hover fill then reaches 8 px past the text and its focus ring 12 px, inside the
  // 16 px padding of the smallest card. A flush button carries an icon, so its spinner takes
  // the icon's place and loading does not change its width.
  flush?: boolean;
};

export function Button({
  variant = "secondary",
  icon: Icon,
  disabled = false,
  loading = false,
  iconOnly = false,
  flush = false,
  className,
  children,
  onClick,
  type = "button",
  ...rest
}: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <button
      {...rest}
      type={type}
      data-button={variant}
      aria-disabled={inactive || undefined}
      aria-busy={loading || undefined}
      data-disabled={disabled || undefined}
      onClick={inactive ? (event) => event.preventDefault() : onClick}
      className={cx(
        "relative inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-pill border-2 text-button",
        "transition-paint duration-150 select-none",
        iconOnly ? "w-11" : flush ? "-ml-2 px-2" : loading && !Icon ? "px-3" : "px-6",
        VARIANTS[variant],
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
      <span className={cx(iconOnly && "sr-only")}>{children}</span>
    </button>
  );
}
