// The skip link that leads every page (DESIGN.md section 10). Hidden until it has focus; then
// a white button shape with a control's 4 px corners, 44 px tall, at the top left of the navy bar.
import { copy } from "../copy";

export function SkipLink({ target = "#main" }: { target?: string }) {
  return (
    <a
      href={target}
      className={
        "sr-only focus:not-sr-only focus:absolute focus:top-1.5 focus:left-[var(--layout-margin)] focus:z-50 " +
        "focus:inline-flex focus:h-11 focus:items-center focus:rounded-sm focus:border focus:border-primary " +
        "focus:bg-surface focus:px-4 focus:text-button focus:text-primary hover:bg-tint"
      }
    >
      {copy.skipLink}
    </a>
  );
}
