import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { DeckApp, deckView } from "./deck/Deck";
import "./styles/app.css";

const root = createRoot(document.getElementById("root")!);

// The design gallery exists only in development and gallery builds. In a production build
// __GALLERY__ is false, so the bundler drops this branch and the gallery's code with it.
if (__GALLERY__ && /^\/gallery(\/|$)/.test(window.location.pathname)) {
  void import("./gallery/Gallery").then(({ Gallery }) =>
    root.render(
      <StrictMode>
        <Gallery path={window.location.pathname} search={window.location.search} />
      </StrictMode>,
    ),
  );
} else if (deckView(window.location.pathname)) {
  // The deck at /present (ticket 47) stands outside the app's frame: no navy bar, no box, and nothing in the app
  // links to it. Any other address under /present is the app's not-found page.
  root.render(
    <StrictMode>
      <DeckApp view={deckView(window.location.pathname)!} />
    </StrictMode>,
  );
} else {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
