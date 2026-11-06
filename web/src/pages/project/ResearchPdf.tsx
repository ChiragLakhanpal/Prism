// "Download as PDF" (ticket 158): the browser's own print writes the PDF, so the button first waits for every picture in
// the print view (ResearchPrint.tsx) to load or fail, saying "<n> of <total> images loaded" beside it, and only then
// calls window.print(). A failed picture counts as finished: its frame or its grid's caption says why. After
// PDF_WAIT_MS it prints anyway, and each picture still loading is marked late, so its words say it did not load in time.
import { useRef, useState } from "react";
import { Button } from "../../components/Button";
import { copy } from "../../copy";

const words = copy.research;
const PDF_WAIT_MS = 25_000;
const PRINTED = "[data-research-print] img";

const frame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
const pause = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, Math.max(0, ms)));

export function PdfButton() {
  const [count, setCount] = useState<{ loaded: number; total: number } | null>(null);
  const busy = useRef(false);

  async function prepare() {
    if (busy.current) return;
    busy.current = true;
    const deadline = Date.now() + PDF_WAIT_MS;
    const seen = new Set<HTMLImageElement>();
    const waits: Promise<void>[] = [];
    let settled = 0;
    const show = () => setCount({ loaded: settled, total: seen.size });
    // Every picture in the print view, the ones a late list (the team's photos) adds included.
    const track = () => {
      for (const image of document.querySelectorAll<HTMLImageElement>(PRINTED)) {
        if (seen.has(image)) continue;
        seen.add(image);
        waits.push(
          new Promise<void>((resolve) => {
            const done = () => {
              settled += 1;
              show();
              resolve();
            };
            if (image.complete) return done();
            image.addEventListener("load", done, { once: true });
            image.addEventListener("error", done, { once: true });
          }),
        );
      }
      show();
    };
    track();
    while (Date.now() < deadline) {
      const before = seen.size;
      await Promise.race([Promise.all(waits), pause(deadline - Date.now())]);
      await frame();
      await frame();
      track();
      if (seen.size === before && settled >= seen.size) break;
    }
    // The wait ran out: each picture still loading says it did not load in time.
    for (const image of seen) {
      if (image.isConnected && !image.complete) {
        image.dataset.imageLate = "true";
        image.dispatchEvent(new Event("error"));
      }
    }
    await frame();
    await frame();
    setCount(null);
    busy.current = false;
    window.print();
  }

  return (
    <>
      <Button variant="primary" loading={count !== null} onClick={() => void prepare()} data-research-pdf>
        {count ? words.pdf.preparing : words.print}
      </Button>
      <span role="status" data-research-pdf-count className="text-caption text-ink-muted">
        {count && words.pdf.loaded(String(count.loaded), String(count.total))}
      </span>
    </>
  );
}
