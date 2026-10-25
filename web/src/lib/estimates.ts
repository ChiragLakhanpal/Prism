// The time estimate in the browser (ticket 26): the viewer's plan-date choice, saved for the package. The choice
// on screen changes at once; it is saved 500 ms after the last move, ticket 15's rule for the plan line, so arrowing
// across the two options sends one save. A failed save keeps the choice on screen and says so. In a preview the
// choice still switches, as section 2's does, and nothing is saved (the server refuses it too).
//
// The same stored value sets the dates section 2 drafts (ticket 27's "Date each step with"), so the two controls
// share planDateChoices, the choice made on this page by its save path: a choice in one shows in the other at once.
import { useCallback, useEffect, useRef, useState } from "react";
import type { PlanDateChoice } from "./api";
import { putJson } from "./api";
import { createStore, useStore } from "./store";

export const PLAN_DATE_SAVE_AFTER_MS = 500;

// The plan-date choice made on this page, by the package's PUT .../plan-dates path.
export const planDateChoices = createStore<Record<string, PlanDateChoice>>({});

export function sharePlanDateChoice(savePath: string, choice: PlanDateChoice) {
  planDateChoices.set((now) => (now[savePath] === choice ? now : { ...now, [savePath]: choice }));
}

export function useSharedPlanDateChoice(savePath: string): PlanDateChoice | null {
  return useStore(planDateChoices)[savePath] ?? null;
}

export type PlanDateChoiceState = {
  chosen: PlanDateChoice | null;
  onChoose: (choice: PlanDateChoice) => void;
  held: boolean;
  failed: boolean;
  // How many saves have landed, so the section can say the choice once each time.
  saved: number;
};

// savePath: PUT .../plan-dates for this package. initial: the choice the estimate route answered with. held: a
// preview, which switches the choice on screen and saves nothing.
export function usePlanDateChoice(savePath: string, initial: PlanDateChoice | null, held: boolean): PlanDateChoiceState {
  const [chosen, setChosen] = useState<PlanDateChoice | null>(initial);
  const [failed, setFailed] = useState(false);
  const [saved, setSaved] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const shared = useSharedPlanDateChoice(savePath);
  // A new answer for the package brings its saved choice; a choice made on this page since then wins.
  const touched = useRef(false);
  useEffect(() => {
    if (!touched.current) setChosen(initial);
  }, [initial]);
  // A choice made in section 2 shows here too.
  useEffect(() => {
    if (shared === null) return;
    touched.current = true;
    setChosen(shared);
  }, [shared]);
  useEffect(() => () => clearTimeout(timer.current), []);
  const onChoose = useCallback(
    (choice: PlanDateChoice) => {
      touched.current = true;
      setChosen(choice);
      sharePlanDateChoice(savePath, choice);
      if (held) return;
      clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        putJson<{ plan_date_choice: PlanDateChoice | null }>(savePath, { choice }).then(
          () => {
            setFailed(false);
            setSaved((count) => count + 1);
          },
          () => setFailed(true),
        );
      }, PLAN_DATE_SAVE_AFTER_MS);
    },
    [held, savePath],
  );
  return { chosen, onChoose, held, failed, saved };
}
