// Who is viewing the Lessons pages (GET /api/lessons/me): the roles that open the reviewer pages and how many items
// wait on each. It loads once a page load, when a Lessons page or the sidebar under Lessons first needs it, and again
// after a save, so the sidebar's counts follow what you did (ticket 102). The reviewer pages read the same answer.
import { useEffect } from "react";
import { getJson } from "./api";
import type { Me } from "./lessons";
import { createStore, useStore } from "./store";

export type MeState = { status: "loading" } | { status: "ready"; me: Me } | { status: "error" };
export const lessonsMe = createStore<MeState>({ status: "loading" });
let asked = false;

export async function refreshLessonsMe() {
  try {
    lessonsMe.set({ status: "ready", me: await getJson<Me>("/api/lessons/me") });
  } catch {
    lessonsMe.set((current) => (current.status === "ready" ? current : { status: "error" }));
  }
}

// The answer, asked for the first time once need is true (a Lessons page always needs it).
export function useLessonsMe(need = true): MeState {
  const me = useStore(lessonsMe);
  useEffect(() => {
    if (!need || asked) return;
    asked = true;
    void refreshLessonsMe();
  }, [need]);
  return me;
}
