// The one box with its intent rules (the 14 brief, sections 4.3 and 6), in the Ask bar at the page's foot (ticket 113):
// it lists what Enter will do as you type, looks up the records an option needs in the background, and does nothing
// until you choose. An ID opens its page; "Ask this" asks the question with the page's scope chip and keeps the
// question in the box, with focus, so you can refine it.
//
// Keys: Down and Up move the option Enter does; Enter does it; Tab closes the list; Escape closes the
// list, then empties the box, and only then reaches the evidence drawer; Backspace in an empty box
// removes the scope chip and says so.
//
// Focused and empty (ticket 112), the list holds its hint, then up to three questions for the page from GET /api/me's
// ask (config/examples.toml's [[ask]]), none chosen: Down or Up moves to one, and Enter or a click puts its words in
// the box and asks it within the page's scope, exactly as "Ask this" does. Typing replaces them with what Enter will
// do.
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { FolderOpen, MessageSquareText, PackagePlus, Table2 } from "lucide-react";
import { copy } from "../copy";
import { formatDate } from "../lib/format";
import { removedScopes, removeScope } from "../lib/answer";
import {
  askRows,
  hrefFor,
  intentKey,
  intentsFor,
  lookUp,
  suggestionsFor,
  suggestionText,
  type AskPage,
  type Found,
  type Intent,
  type Lookup,
} from "../lib/intents";
import { boxMode, startPlanning } from "../lib/packages";
import { navigate } from "../lib/router";
import { allows, appliedView } from "../lib/view";
import { useStore } from "../lib/store";
import { currentLanguage, ENGLISH, languageName, workingLanguage } from "../lib/lang";
import { OneBox, type BoxOption } from "./OneBox";
import { Fill } from "./Fill";
import { MonoWords } from "./MonoWords";
import { wholeDate } from "./NumFrom";
import { RETURNING } from "./Popover";

const LOOKUP_DELAY_MS = 150;
const ICONS = { project: FolderOpen, loan: FolderOpen, activity: Table2 };

// An ID in mono. A P-code or a loan number (12 characters or fewer) moves to the next line whole; a STEP reference
// takes the scope chip's rule, MonoWords: each part between spaces moves to the next line whole, and breaks after a
// hyphen only when it is wider than the line (DESIGN.md section 5, Reference words; ticket 59).
const mono = (text: string) => (text.length <= 12 ? <span className="font-mono whitespace-nowrap">{text}</span> : <MonoWords text={text} />);

function idLabel(intent: Intent): ReactNode {
  const words = copy.box.option;
  if (intent.kind === "project") return <Fill template={words.project} slots={{ pcode: mono(intent.id) }} />;
  if (intent.kind === "loan") return <Fill template={words.loan} slots={{ loan: mono(intent.id) }} />;
  return <Fill template={words.activity} slots={{ step_ref: mono(intent.id) }} />;
}

function foundLine(found: Found): ReactNode {
  const words = copy.box.option;
  if (found.kind === "project") return words.projectLine(found.name, found.country);
  if (found.kind === "loan") return <Fill template={words.loanLine} slots={{ pcode: mono(found.pcode), name: found.name ?? "" }} />;
  // A plan's date never breaks inside itself (ticket 59, criterion 5).
  return <Fill template={words.activityLine(found.agency, wholeDate(formatDate(found.planDate)))} slots={{ pcode: mono(found.pcode) }} />;
}

export type Choice = { kind: "ask" } | { kind: "id"; intent: Intent } | { kind: "plan"; held?: boolean } | { kind: "go"; href: string };

// What the box lists for this input, scope chip and lookups so far: the options, best first, what
// choosing each does, and the lines under the list for an ID no record holds or a lookup that failed.
// Free text also offers "Plan a package from this sentence" (ticket 15), never first unless the Packages
// tab's "Plan a package" put the box in plan mode. In check mode, a project ID lists each implementing
// agency's latest plan to check, then the project itself.
export function boxList(
  value: string,
  chip: string | null,
  lookups: Record<string, Lookup>,
  mode: "plan" | "check" | null = null,
  view: "staff" | "piu" | "public" = "staff",
) {
  const listed = boxListOf(value, chip, lookups);
  const text = value.trim();
  if (mode === "check") {
    const project = listed.ids.length === 1 && listed.ids[0].kind === "project" ? listed.ids[0] : null;
    const lookup = project ? lookups[intentKey(project)] : undefined;
    if (project && lookup?.status === "found" && lookup.found.kind === "project") {
      const plans = lookup.found.plans ?? [];
      const options: BoxOption[] = plans.map((plan) => ({
        key: `check:${plan.agencyId}`,
        icon: Table2,
        label: copy.box.option.checkPlan(plan.agency, wholeDate(formatDate(plan.planDate))),
        line: <Fill template={copy.box.option.checkPlanLine} slots={{ pcode: mono(project.id) }} />,
      }));
      const choices: Choice[] = plans.map((plan) => ({ kind: "go", href: `/projects/${project.id}/procurement/${plan.agencyId}` }));
      const notes = plans.length === 0 ? [<Fill template={copy.box.option.noPlan} slots={{ pcode: mono(project.id) }} />] : [];
      return { ...listed, options: [...options, ...listed.options], choices: [...choices, ...listed.choices], notes: [...notes, ...listed.notes] };
    }
    return listed;
  }
  // The public view has no packages, so it never offers to plan one; an implementing agency preview lists the
  // option held, with its reason, so it stays discoverable (the 15 brief, section 7.1).
  if (!text || !listed.askFirst || view === "public") return listed;
  const held = view === "piu";
  const planOption: BoxOption = {
    key: "plan",
    icon: PackagePlus,
    label: copy.box.option.plan,
    line: held ? copy.box.option.planPreviewOff : copy.box.option.planLine,
    disabled: held,
  };
  const planChoice: Choice = { kind: "plan", held };
  if (mode === "plan" && !held) {
    return { ...listed, options: [planOption, ...listed.options], choices: [planChoice, ...listed.choices] };
  }
  return { ...listed, options: [...listed.options, planOption], choices: [...listed.choices, planChoice] };
}

function boxListOf(value: string, chip: string | null, lookups: Record<string, Lookup>) {
  const { ids, askFirst } = intentsFor(value);
  const notes: ReactNode[] = [];
  const idOptions: { option: BoxOption; intent: Intent }[] = [];
  for (const intent of ids) {
    const lookup = lookups[intentKey(intent)];
    const words = copy.box;
    if (lookup?.status === "missing") {
      if (!intent.needsLookup) notes.push(<Fill template={words.notFound[intent.kind]} slots={{ id: mono(intent.id) }} />);
      continue;
    }
    if (lookup?.status === "failed") {
      notes.push(<Fill template={words.lookupFailed} slots={{ id: mono(intent.id) }} />);
      continue;
    }
    const found = lookup?.status === "found" ? lookup.found : null;
    if (intent.needsLookup && !found) continue;
    const shown: Intent = found?.kind === "loan" ? { ...intent, id: found.loan } : intent;
    idOptions.push({
      intent,
      option: {
        key: intentKey(intent),
        icon: ICONS[intent.kind],
        label: idLabel(shown),
        line: found ? foundLine(found) : <Fill template={words.option.lookingUp} slots={{ id: mono(intent.id) }} />,
      },
    });
  }
  const askOption: BoxOption = {
    key: "ask",
    icon: MessageSquareText,
    label: copy.box.option.ask,
    line: (
      <>
        {chip ? <Fill template={copy.box.option.askWithin} slots={{ id: mono(chip) }} /> : copy.box.option.askAcross}
        {/* The language of the answer, before you press Enter, when it is not English (the 42 brief, section 5.3). */}
        {currentLanguage() !== ENGLISH && copy.box.option.askLanguage(languageName(currentLanguage()))}
      </>
    ),
  };
  const choices: Choice[] = [];
  const options: BoxOption[] = [];
  const addAsk = () => {
    choices.push({ kind: "ask" });
    options.push(askOption);
  };
  if (askFirst) addAsk();
  for (const { option, intent } of idOptions) {
    choices.push({ kind: "id", intent });
    options.push(option);
  }
  if (!askFirst) addAsk();
  return { ids, options, choices, notes, askFirst };
}

export function IntentBox({
  scope,
  scopeKind,
  page = null,
  onAsk,
}: {
  // The page's scope: a P-code on a project page, a STEP reference or package on a package page.
  scope: string | null;
  scopeKind: "project" | "package";
  // Which suggestions the page shows (ticket 112): a package's, a project's or a plan check's; null shows Home's.
  page?: AskPage | null;
  onAsk: (question: string, scope: string | null) => void;
}) {
  const [value, setValue] = useState("");
  // Whether the list may show: set by a focus the person moved, a click, Down or typing; cleared by Escape, Tab, a
  // choice and focus the page gave back.
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [focused, setFocused] = useState(false);
  // The suggestion Enter asks, or -1 for none.
  const [picked, setPicked] = useState(-1);
  const rows = useStore(askRows);
  const [lookups, setLookups] = useState<Record<string, Lookup>>({});
  const [said, setSaid] = useState("");
  const asked = useRef(new Map<string, Promise<Lookup>>());
  const input = useRef<HTMLInputElement>(null);
  const removed = useStore(removedScopes);
  // The "Ask this" line names the language of answers when it is not English, so it follows a new choice (ticket 42).
  useStore(workingLanguage);
  const asked_mode = useStore(boxMode);
  const mode = asked_mode?.mode ?? null;

  // A new page brings its own scope back, and says nothing about the last one.
  useEffect(() => setSaid(""), [scope]);
  const chip = scope && !removed.has(scope) ? scope : null;

  // The Packages tab's buttons (and "Change the sentence") put the box in a mode: it takes focus, with the
  // sentence to change in it, if there is one (the 15 brief, section 7.1).
  useEffect(() => {
    if (!asked_mode) return;
    setValue(asked_mode.text ?? "");
    setActive(0);
    const element = input.current;
    if (!element) return;
    element.focus({ preventScroll: true });
    element.setSelectionRange(element.value.length, element.value.length);
    setOpen(Boolean(asked_mode.text));
  }, [asked_mode?.at]);

  // Whether the box offers to plan a package, from the view the server applied (the roles file's [views]): not where
  // the view has no packages, held where it keeps packages but not planning one (a preview), and offered otherwise.
  const shownView = useStore(appliedView);
  const view = !allows("packages", shownView) ? "public" : !allows("plan_package", shownView) ? "piu" : "staff";
  const { ids, options, choices, notes } = boxList(value, chip, lookups, mode, view);
  const suggested = suggestionsFor(rows, page, chip);
  const suggesting = open && focused && value === "" && !mode && suggested.items.length > 0;
  const suggestion = Math.min(picked, suggested.items.length - 1);

  const lookupOf = (intent: Intent) => {
    const key = intentKey(intent);
    let promise = asked.current.get(key);
    if (!promise) {
      promise = lookUp(intent, new AbortController().signal);
      asked.current.set(key, promise);
      setLookups((now) => ({ ...now, [key]: { status: "pending" } }));
      void promise.then((result) => {
        // A lookup that failed may work next time.
        if (result.status === "failed") asked.current.delete(key);
        setLookups((now) => ({ ...now, [key]: result }));
      });
    }
    return promise;
  };

  // Lookups wait until typing pauses, and only fill in the second line.
  useEffect(() => {
    if (ids.length === 0) return;
    const timer = setTimeout(() => ids.forEach(lookupOf), LOOKUP_DELAY_MS);
    return () => clearTimeout(timer);
    // ids is derived from value.
  }, [value]);

  const current = Math.min(active, options.length - 1);

  const go = (found: Found) => {
    setValue("");
    setOpen(false);
    const to = new URL(hrefFor(found), window.location.origin);
    // The same page with another activity named: set the hash, so the plan check follows it.
    if (to.pathname === window.location.pathname && to.search === window.location.search) window.location.hash = to.hash;
    else navigate(to.pathname + to.search + to.hash);
  };

  const choose = async (index: number) => {
    const choice = choices[index];
    if (!choice || !value.trim()) return;
    if (choice.kind === "ask") {
      setOpen(false);
      boxMode.set(null);
      onAsk(value.trim(), chip);
      return;
    }
    // The only way the box makes a package (the 15 brief, section 6): the workflow starts, and the reading
    // page shows it at once.
    if (choice.kind === "plan") {
      if (choice.held) return;
      startPlanning(value.trim());
      setValue("");
      setOpen(false);
      boxMode.set(null);
      navigate("/packages/new");
      return;
    }
    if (choice.kind === "go") {
      setValue("");
      setOpen(false);
      boxMode.set(null);
      navigate(choice.href);
      return;
    }
    const { intent } = choice;
    if (intent.kind === "project") {
      go({ kind: "project", pcode: intent.id, name: "", country: null });
      return;
    }
    const result = await lookupOf(intent);
    if (result.status === "found") go(result.found);
  };

  // A suggestion's words go into the box, and it is asked within the page's scope (or, on Home, its own example),
  // exactly as "Ask this" asks: the question stays in the box, with focus, so you can refine it.
  const chooseSuggestion = (index: number) => {
    const item = suggested.items[index];
    if (!item) return;
    const question = suggestionText(item);
    setValue(question);
    setPicked(-1);
    setOpen(false);
    onAsk(question, item.within);
  };

  const removeChip = () => {
    if (!chip) return;
    removeScope(chip);
    setSaid(copy.box.scopeRemoved);
    input.current?.focus({ preventScroll: true });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    event.currentTarget.removeAttribute(RETURNING);
    const listShown = open && value.trim().length > 0 && options.length > 0;
    if ((event.key === "ArrowDown" || event.key === "ArrowUp") && value === "" && !mode && suggested.items.length > 0) {
      event.preventDefault();
      if (!suggesting) {
        setOpen(true);
        return;
      }
      const count = suggested.items.length;
      if (event.key === "ArrowDown") setPicked(suggestion < 0 ? 0 : (suggestion + 1) % count);
      else setPicked(suggestion < 0 ? count - 1 : (suggestion - 1 + count) % count);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!value.trim()) return;
      event.preventDefault();
      if (!listShown) {
        setOpen(true);
        return;
      }
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((current + step + options.length) % options.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (event.nativeEvent.isComposing) return;
      if (suggesting && suggestion >= 0) chooseSuggestion(suggestion);
      else void choose(listShown ? current : 0);
    } else if (event.key === "Escape") {
      // Innermost first: the list, then the text. With both gone, Escape reaches the drawer.
      if (listShown || suggesting) {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        setPicked(-1);
      } else if (value) {
        event.preventDefault();
        event.stopPropagation();
        setValue("");
      } else if (mode) {
        event.preventDefault();
        event.stopPropagation();
        boxMode.set(null);
      }
    } else if (event.key === "Tab") {
      setOpen(false);
    } else if (event.key === "Backspace" && chip && value === "" && event.currentTarget.selectionStart === 0) {
      event.preventDefault();
      removeChip();
    }
  };

  return (
    <OneBox
      value={value}
      inputRef={input}
      onChange={(next) => {
        setValue(next);
        setActive(0);
        setPicked(-1);
        setOpen(true);
      }}
      options={options}
      notes={notes}
      open={open}
      active={current}
      scope={chip}
      scopeKind={scopeKind}
      onRemoveScope={removeChip}
      onChoose={(index) => void choose(index)}
      onKeyDown={onKeyDown}
      onPointerDown={() => {
        input.current?.removeAttribute(RETURNING);
        setOpen(true);
      }}
      onFocusChange={(now) => {
        // Focus the page gave back (AnswerPanel's close) leaves the list shut until a key or a click.
        const given = input.current?.hasAttribute(RETURNING) ?? false;
        if (!now) input.current?.removeAttribute(RETURNING);
        // Leaving the box ends its mode.
        if (!now && mode) boxMode.set(null);
        setFocused(now);
        setPicked(-1);
        setOpen(now && !given);
      }}
      suggestions={
        suggesting
          ? {
              name: copy.box.suggest.group[suggested.page],
              options: suggested.items.map((item, index) => ({
                key: `suggest:${index}:${item.key}`,
                icon: MessageSquareText,
                label: <Fill template={item.template} slots={{ id: item.id ? mono(item.id) : "" }} />,
              })),
            }
          : null
      }
      suggestionActive={suggestion}
      onChooseSuggestion={chooseSuggestion}
      modePlaceholder={mode === "plan" ? copy.box.mode.planPlaceholder : mode === "check" ? copy.box.mode.checkPlaceholder : undefined}
      modePlaceholderShort={mode === "plan" ? copy.box.mode.planPlaceholderShort : undefined}
      modeHelp={mode === "plan" ? copy.box.mode.planHelp : undefined}
    >
      <p role="status" className="sr-only">
        {said}
      </p>
    </OneBox>
  );
}
