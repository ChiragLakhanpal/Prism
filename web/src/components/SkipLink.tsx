// The skip link that leads every page (DESIGN.md section 10). Hidden until it has focus; then
// a white button shape with a control's 4 px corners, 44 px tall, 8 px below the navy bar, over the
// page at its content edge, so it never covers the logo or the wordmark (ticket 93). The bar is its
// positioned parent.
import { copy } from "../copy";

export function SkipLink({ target = "#main" }: { target?: string }) {
  return (
    <a
      href={target}
      data-skip-link
      className={
        "sr-only focus:not-sr-only focus:absolute focus:top-full focus:left-[calc(var(--nav-width)+var(--window-margin))] focus:z-50 focus:mt-2 " +
        "focus:inline-flex focus:h-11 focus:items-center focus:rounded-sm focus:border focus:border-primary " +
        "focus:bg-surface focus:px-4 focus:text-button focus:text-primary hover:bg-tint"
      }
    >
      {copy.skipLink}
    </a>
  );
}
