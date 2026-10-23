// A text link: primary and underlined, so it never depends on color alone (DESIGN.md
// section 10). Links navigate; buttons act. The 4 px of padding above and below makes the
// hit area at least 24 px tall, even in 14 px text, without moving the line.
import type { ComponentProps } from "react";
import { cx } from "../lib/cx";

export function TextLink({ className, ...rest }: ComponentProps<"a">) {
  return (
    <a
      {...rest}
      className={cx(
        "py-1 text-primary underline decoration-1 underline-offset-3 transition-paint duration-150",
        "hover:text-link-hover active:text-primary-pressed",
        className,
      )}
    />
  );
}
