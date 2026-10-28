// Home's answer (ticket 41; src/strata/server/home.py): the briefing's sentences, the Start here strip's links, the
// lines under "Worth knowing" and the drafts under "Waiting for you". The server counts, compares dates and picks
// every count word; the page writes dates and numbers through Num and counts nothing.
import { createStore } from "./store";
import type { DraftRow } from "./drafts";

// A part of a sentence the server wrote: words, a count with the word it chose (and, in the briefing, the kind it
// counts and the ids of what it counts), a date, a year, a STEP reference, a P-code, an amount as written, or a number.
// An amount or a number in a line names the value it is (what, ticket 96), for its tooltip; an amount in millions
// carries the plan row's own value to the cent (exact).
export type HomeValue = "millions" | "estimated" | "actual" | "daysToClose";
export type HomeSegment =
  | { text: string }
  | { count: number; word: string; kind?: string; ids?: string[] }
  | { date: string | null; style?: "short" }
  | { year: number }
  | { ref: string }
  | { pid: string }
  | { written: string; what?: HomeValue; exact?: string }
  | { number: number; what?: HomeValue };

export type HomeLine = {
  kind: "activity" | "project" | "lesson" | "public";
  id: string;
  key: string;
  status: string;
  reason: string;
  example: boolean;
  plan?: string;
  segments: HomeSegment[];
  source: { evidence_id: string; kind: string; date?: string | null; version?: number; agency?: string; pid?: string };
  action: { key: string; href: string; hidden: string };
  differs: null;
};

export type HomePlan = {
  document_id: string;
  project_id: string;
  project_name: string | null;
  implementing_agency?: string;
  agency_id?: string;
  plan_date: string;
  disclosed_on?: string;
};

export type HomeAnswer = {
  view: "staff" | "piu" | "public";
  preview: boolean;
  today: string;
  as_of: string | null;
  // phrase: the window as the server words it ("the past seven days"), which the page writes as it is.
  window: { days: number; start: string; end: string; data_through: string | null; phrase: HomeSegment[] } | null;
  briefing: { sentences: HomeSegment[][]; plans: HomePlan[] };
  start_here: { visible: boolean; links: { key: string; href: string; pid: string | null }[] };
  worth: {
    kind: "staff" | "agency" | "public";
    lines: HomeLine[];
    fold_after: number;
    partial: number | null;
    checked_on: string;
    through: string;
    empty: "first_run" | "quiet" | "nothing_marked" | "no_plan" | "nothing_behind" | "no_closed" | null;
    followed?: number;
  };
  waiting: { rows: (DraftRow & { example?: boolean })[]; total: number; more: boolean; reason: "preview" | "asof" | "public" | null };
  public: { total: number } | null;
};

// Whether Home shows its Start here strip, from GET /api/me, so the page keeps its room before Home's answer arrives.
export const startHereVisible = createStore<boolean>(false);

export const HOME_PATH = "/api/home";
export const START_HERE_PATH = "/api/home/start-here";
