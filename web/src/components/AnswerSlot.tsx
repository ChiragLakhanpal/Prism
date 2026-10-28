// The answer a workspace page draws itself (ticket 98; DESIGN.md section 4, Page layouts, Workspace): on a page that
// routes.ts's ANSWER_IN_PAGE names, App.tsx hands the answer panel down here instead of drawing it at the top of the
// page column, and the page passes it to Workspace's answer slot, so it takes columns 1 to 7 above the page head and
// beside the side panel. useAnswerInPage gives that panel, or null when no answer is open on this history entry.
import { createContext, useContext, type ReactNode } from "react";

export const AnswerSlot = createContext<ReactNode>(null);

export function useAnswerInPage(): ReactNode {
  return useContext(AnswerSlot);
}
