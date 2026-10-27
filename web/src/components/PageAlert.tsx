// The page's alert slot (DESIGN.md section 5, Page header; the shell redesign plan, 8.5; ticket 94). Every page has one
// place for alerts, above its head and above an answer to a question: the frame's own alerts (access, identity, the
// address), the preview and as-of banners, and, when a page's one read failed, that page's error alert with "Try
// again", under which the page draws only its head, whose h1 names the page. A page puts its alert there with
// PageAlert. Outside the app's frame, as in the design gallery, the alert stays where the page draws it.
import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";

// The slot's element, which App.tsx provides once it is in the page.
export const AlertSlot = createContext<HTMLElement | null>(null);

export function PageAlert({ children }: { children: ReactNode }) {
  const slot = useContext(AlertSlot);
  return slot ? createPortal(children, slot) : children;
}
