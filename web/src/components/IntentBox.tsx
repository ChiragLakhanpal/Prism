// The band's one box with its intent rules (the 14 brief, sections 4.3 and 6): it lists what Enter will
// do as you type, looks up the records an option needs in the background, and does nothing until you
// choose. An ID opens its page; "Ask this" asks the question with the page's scope chip and keeps the
// question in the box, with focus, so you can refine it.
//
// Keys: Down and Up move the option Enter does; Enter does it; Tab closes the list; Escape closes the
// list, then empties the box, and only then reaches the evidence drawer; Backspace in an empty box
// removes the scope chip and says so.
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { FolderOpen, MessageSquareText, Table2 } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { removedScopes, removeScope } from "../lib/answer";
import { hrefFor, intentKey, intentsFor, lookUp, type Found, type Intent, type Lookup } from "../lib/intents";
import { navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { OneBox, type BoxOption } from "./BoxBand";
import { Fill } from "./Fill";
import { RETURNING } from "./Popover";

const LOOKUP_DELAY_MS = 150;
const ICONS = { project: FolderOpen, loan: FolderOpen, activity: Table2 };

// An ID in mono. A P-code or a loan number (12 characters or fewer) moves to the next line whole; a
// STEP reference may still break after its hyphens (DESIGN.md section 5, Page header).
const mono = (text: string) => <span className={cx("font-mono", text.length <= 12 && "whitespace-nowrap")}>{text}</span>;

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
  return <Fill template={words.activityLine(found.agency, formatDate(found.planDate))} slots={{ pcode: mono(found.pcode) }} />;
}

export type Choice = { kind: "ask" } | { kind: "id"; intent: Intent };

// What the box lists for this input, scope chip and lookups so far: the options, best first, what
// choosing each does, and the lines under the list for an ID no record holds or a lookup that failed.
export function boxList(value: string, chip: string | null, lookups: Record<string, Lookup>) {
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
    line: chip ? <Fill template={copy.box.option.askWithin} slots={{ id: mono(chip) }} /> : copy.box.option.askAcross,
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
  return { ids, options, choices, notes };
}

export function IntentBox({
  scope,
  scopeKind,
  onAsk,
}: {
  // The page's scope: a P-code on a project page, a STEP reference or package on a package page.
  scope: string | null;
  scopeKind: "project" | "package";
  onAsk: (question: string, scope: string | null) => void;
}) {
  const [value, setValue] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [lookups, setLookups] = useState<Record<string, Lookup>>({});
  const [said, setSaid] = useState("");
  const asked = useRef(new Map<string, Promise<Lookup>>());
  const input = useRef<HTMLInputElement>(null);
  const removed = useStore(removedScopes);

  // A new page brings its own scope back, and says nothing about the last one.
  useEffect(() => setSaid(""), [scope]);
  const chip = scope && !removed.has(scope) ? scope : null;

  const { ids, options, choices, notes } = boxList(value, chip, lookups);

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
      onAsk(value.trim(), chip);
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

  const removeChip = () => {
    if (!chip) return;
    removeScope(chip);
    setSaid(copy.box.scopeRemoved);
    input.current?.focus();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    event.currentTarget.removeAttribute(RETURNING);
    const listShown = open && value.trim().length > 0 && options.length > 0;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
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
      void choose(listShown ? current : 0);
    } else if (event.key === "Escape") {
      // Innermost first: the list, then the text. With both gone, Escape reaches the drawer.
      if (listShown) {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
      } else if (value) {
        event.preventDefault();
        event.stopPropagation();
        setValue("");
      }
    } else if (event.key === "Tab") {
      setOpen(false);
    } else if (event.key === "Backspace" && chip && value === "" && event.currentTarget.selectionStart === 0) {
      event.preventDefault();
      removeChip();
    }
  };

  return (
    <>
      <OneBox
        value={value}
        inputRef={input}
        onChange={(next) => {
          setValue(next);
          setActive(0);
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
        onFocusChange={(focused) => {
          // Focus the page gave back (AnswerPanel's close) leaves the list shut until a key.
          const given = input.current?.hasAttribute(RETURNING) ?? false;
          if (!focused) input.current?.removeAttribute(RETURNING);
          setOpen(focused && !given && value.trim().length > 0);
        }}
      />
      <p role="status" className="sr-only">
        {said}
      </p>
    </>
  );
}
