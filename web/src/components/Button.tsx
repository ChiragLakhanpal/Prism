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

// Disabled: surface-2 with ink-muted text (5.67:1), whatever the variant. A loading button
// keeps its variant's look and shows a spinner instead.
const DISABLED =
  "data-disabled:cursor-not-allowed data-disabled:border-line data-disabled:bg-surface-2 data-disabled:text-ink-muted " +
  "data-disabled:hover:border-line data-disabled:hover:bg-surface-2";

export type ButtonProps = Omit<ComponentProps<"button">, "disabled"> & {
  variant?: ButtonVariant;
  icon?: LucideIcon;
  // Disabled buttons stay focusable, so a keyboard user can still find them and read why.
  disabled?: boolean;
  // While loading, the label stays in place and the icon turns into a spinner.
  loading?: boolean;
  // An icon-only button needs an aria-label from the copy file.
  iconOnly?: boolean;
};

export function Button({
  variant = "secondary",
  icon: Icon,
  disabled = false,
  loading = false,
  iconOnly = false,
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
        iconOnly ? "w-11" : "px-6",
        VARIANTS[variant],
        DISABLED,
        loading && "cursor-progress",
        className,
      )}
    >
      {Icon && !loading && <Icon aria-hidden="true" className="size-4 shrink-0" />}
      {loading && Icon && <LoaderCircle aria-hidden="true" className="size-4 shrink-0 animate-spin" />}
      {loading && !Icon && (
        <span className="absolute inset-0 flex items-center justify-center">
          <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
        </span>
      )}
      {/* opacity, not visibility, so the hidden label still names the button. */}
      <span className={cx(loading && !Icon && "opacity-0", iconOnly && "sr-only")}>{children}</span>
    </button>
  );
}
