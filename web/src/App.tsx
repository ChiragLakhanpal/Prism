// The web shell, in the frame every page shares (web/src/components/Frame.tsx): the navy bar
// with its skip link, the box band, the page and the footer. The page says who is viewing.
// Ticket 06 adds the logo, the freshness stamp, the routes and Home's own content.
//
// Who is viewing, in four states: checking (a muted line that says so), signed in (a sentence
// with the name), signed out (a sentence that says how to sign in) and unreachable (an error
// alert above the title, with "Try again").
import { useEffect, useState } from "react";
import { Alert } from "./components/Alert";
import { BoxBand, OneBox } from "./components/BoxBand";
import { Button } from "./components/Button";
import { Frame } from "./components/Frame";
import { TopNav, type Viewer } from "./components/TopNav";
import { getJson, type Me } from "./lib/api";
import { createStore, useStore } from "./lib/store";
import { cx } from "./lib/cx";
import { copy } from "./copy";

type ViewerState =
  | { status: "checking" }
  | { status: "signed-in"; name: string; email: string | null }
  | { status: "signed-out" }
  | { status: "unreachable" };

const viewer = createStore<ViewerState>({ status: "checking" });

async function loadViewer(signal: AbortSignal) {
  viewer.set({ status: "checking" });
  try {
    const me = await getJson<Me>("/api/me", { signal });
    const name = me.name ?? me.email;
    viewer.set(me.signed_in && name ? { status: "signed-in", name, email: me.email } : { status: "signed-out" });
  } catch {
    if (!signal.aborted) viewer.set({ status: "unreachable" });
  }
}

// What the view pill's popover says about who is signed in.
function navViewer(state: ViewerState): Viewer {
  if (state.status === "checking") return { status: "loading" };
  if (state.status === "signed-in" && state.email) return { status: "signed-in", email: state.email };
  return { status: "error" };
}

function Box() {
  const [value, setValue] = useState("");
  return <OneBox value={value} onChange={setValue} below={copy.box.notReady} />;
}

// The line under the title that says who is viewing.
function viewerLine(state: Exclude<ViewerState, { status: "unreachable" }>): string {
  if (state.status === "checking") return copy.viewer.checking;
  if (state.status === "signed-in") return copy.viewer.signedIn(state.name);
  return copy.viewer.signedOut;
}

export function App() {
  const state = useStore(viewer);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void loadViewer(controller.signal);
    return () => controller.abort();
  }, [attempt]);

  return (
    <Frame nav={<TopNav home viewer={navViewer(state)} />} band={<BoxBand box={<Box />} />}>
      <div className="layout layout-grid pt-10">
        {/* The 06 brief's alert slot: above the title, columns 1 to 8, 24 px under it. */}
        <div className="col-span-12 md:col-span-8">
          {state.status === "unreachable" && (
            <Alert
              state="error"
              live="alert"
              className="mb-6"
              action={
                <Button variant="secondary" onClick={() => setAttempt(attempt + 1)}>
                  {copy.answer.tryAgain}
                </Button>
              }
            >
              {copy.viewer.unreachable}
            </Alert>
          )}
          <h1 className="text-h1 text-ink-heading">{copy.appName}</h1>
          {state.status !== "unreachable" && (
            <p role="status" className={cx("mt-2 text-body", state.status === "checking" ? "text-ink-muted" : "text-ink")}>
              {viewerLine(state)}
            </p>
          )}
        </div>
      </div>
    </Frame>
  );
}
