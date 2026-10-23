import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
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
} else {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
