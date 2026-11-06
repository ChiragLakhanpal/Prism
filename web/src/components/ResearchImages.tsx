// The pictures of a Deep research brief, on the tab and on paper (ticket 158): the Sentinel-2 tiles, which Prism serves
// (tileRoute; src/strata/server/research_tiles.py), and the team's field photos. No frame is ever blank without a
// sentence: a tile that fails leaves its cell in surface-2 and the grid's caption says how many did not load; a photo
// that fails says so in its frame. "Download as PDF" (ResearchPdf.tsx) marks a picture still loading when its wait
// runs out with data-image-late and sends it an error event, so the words say it did not load in time.
import { useCallback, useState, type SyntheticEvent } from "react";
import { copy } from "../copy";
import { tileRoute } from "../lib/research";
import { cx } from "../lib/cx";

export type Failure = "failed" | "late";

function failureOf(event: SyntheticEvent<HTMLImageElement>): Failure {
  return event.currentTarget.dataset.imageLate ? "late" : "failed";
}

// Which tiles of a figure failed, by their address, and why.
export function useTileFailures() {
  const [failures, setFailures] = useState<Record<string, Failure>>({});
  const fail = useCallback((url: string, why: Failure) => setFailures((now) => (now[url] ? now : { ...now, [url]: why })), []);
  return [failures, fail] as const;
}

// The sentences a figure's caption gains for the tiles of each year that did not load.
export function tileSentences(grids: string[][], years: string[], failures: Record<string, Failure>): string[] {
  const words = copy.research;
  const said: string[] = [];
  grids.forEach((tiles, index) => {
    const shown = tiles.slice(0, 9);
    const total = String(shown.length);
    const failed = shown.filter((url) => failures[url] === "failed").length;
    const late = shown.filter((url) => failures[url] === "late").length;
    if (failed > 0 && failed === shown.length) said.push(words.tilesNone(total, years[index]));
    else if (failed > 0) said.push(words.tilesFailed(String(failed), total, years[index]));
    if (late > 0) said.push(words.tilesLate(String(late), total, years[index]));
  });
  return said;
}

// One tile through Prism's route, 256 pixels square as EOX serves it; a tile that failed is its cell in surface-2.
export function Tile({ url, failed, onFail, className }: { url: string; failed?: Failure; onFail: (url: string, why: Failure) => void; className?: string }) {
  if (failed) return <span aria-hidden="true" data-tile-failed={failed} className={cx("block aspect-square bg-surface-2", className)} />;
  return <img src={tileRoute(url)} alt="" width={256} height={256} data-tile className={className} onError={(event) => onFail(url, failureOf(event))} />;
}

// A field photo in a fixed 4:3 frame on surface-2, the whole picture shown (never cropped); a photo that does not
// come says so in its frame.
export function PhotoFrame({ src, className }: { src: string; className?: string }) {
  const [failed, setFailed] = useState<Failure | null>(null);
  const words = copy.research.photos;
  return (
    <div data-photo-frame={failed ?? "shown"} className={cx("photo-frame relative flex aspect-[4/3] w-full items-center justify-center overflow-hidden border border-line bg-surface-2", className)}>
      {failed ? (
        <p className="m-0 px-4 text-center text-small text-ink-muted">{failed === "late" ? words.notLoadedLate : words.notLoaded}</p>
      ) : (
        <img src={src} alt="" width={800} height={600} className="block h-full w-full object-contain" onError={(event) => setFailed(failureOf(event))} />
      )}
    </div>
  );
}
