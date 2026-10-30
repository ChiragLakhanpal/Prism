// Whether the frame is at least this wide, in rem: the width the @container/frame queries test (Frame.tsx's frame, the
// window less the sidebar), which the evidence drawer does not narrow. It is usePageAtLeast's twin, for a part whose
// place in the DOM must change with the frame so that the reading order follows what the eye sees: the package
// workspace's step tracker sits in the side column from a frame of 75rem and after zone 1 below it, and renders in
// one place only (ticket 130). Styling alone stays with the container queries.
import type { RefObject } from "react";
import { useWidthAtLeast } from "./usePageAtLeast";

export function useFrameAtLeast(inside: RefObject<HTMLElement | null>, rem: number): boolean {
  return useWidthAtLeast(inside, "[data-frame]", rem);
}
