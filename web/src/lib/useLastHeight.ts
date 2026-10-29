// A ready part's last height, kept while it shows, so a rerun's skeleton can hold it and the sections under it stay
// put (ticket 59). The ref goes on the ready part; the height is null until it has been drawn once.
import { useLayoutEffect, useRef, useState } from "react";

export function useLastHeight(shown: boolean, key: unknown) {
  const ref = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!shown || !element) return;
    const keep = () => setHeight(element.getBoundingClientRect().height);
    keep();
    const watch = new ResizeObserver(keep);
    watch.observe(element);
    return () => watch.disconnect();
  }, [shown, key]);
  return [ref, height] as const;
}
