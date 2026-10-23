// The web shell: unstyled until the design-system ticket. It shows who is viewing and the footer.
import { useEffect } from "react";
import { getJson, type Me } from "./lib/api";
import { createStore, useStore } from "./lib/store";
import { copy } from "./copy";

type ViewerState =
  | { status: "checking" }
  | { status: "signed-in"; name: string }
  | { status: "signed-out" }
  | { status: "unreachable" };

const viewer = createStore<ViewerState>({ status: "checking" });

async function loadViewer(signal: AbortSignal) {
  try {
    const me = await getJson<Me>("/api/me", { signal });
    const name = me.name ?? me.email;
    viewer.set(me.signed_in && name ? { status: "signed-in", name } : { status: "signed-out" });
  } catch {
    if (!signal.aborted) viewer.set({ status: "unreachable" });
  }
}

function viewerLine(state: ViewerState): string {
  switch (state.status) {
    case "checking":
      return copy.viewer.checking;
    case "signed-in":
      return copy.viewer.signedIn(state.name);
    case "signed-out":
      return copy.viewer.signedOut;
    case "unreachable":
      return copy.viewer.unreachable;
  }
}

export function App() {
  const state = useStore(viewer);

  useEffect(() => {
    const controller = new AbortController();
    void loadViewer(controller.signal);
    return () => controller.abort();
  }, []);

  return (
    <>
      <a href="#main">{copy.skipLink}</a>
      <header>
        <a href="/">{copy.appName}</a>
      </header>
      <main id="main">
        <h1>{copy.appName}</h1>
        <p role="status">{viewerLine(state)}</p>
      </main>
      <footer>
        <p>{copy.footer}</p>
      </footer>
    </>
  );
}
