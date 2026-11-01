// The deck's door (the user's request of October 31, 2026). The App's server hands out the deck's code, its data and
// the study guide's diagrams only after the password (src/strata/server/deck_door.py), so the door asks for it first
// and loads the deck once the server says it may. The door is in the app's first download, so it imports nothing
// from the deck, and its words are in the app's copy file.
import { useEffect, useId, useState, type ComponentType, type FormEvent } from "react";
import { Button } from "../components/Button";
import { copy } from "../copy";
import type { DeckView } from "./view";

type Deck = ComponentType<{ view: DeckView }>;
type Door = "asking" | "locked" | "wrong" | "failed" | "open";

export function DeckDoor({ view }: { view: DeckView }) {
  const words = copy.deckDoor;
  const [door, setDoor] = useState<Door>("asking");
  const [deck, setDeck] = useState<{ Deck: Deck } | null>(null);
  const [password, setPassword] = useState("");
  const id = useId();
  const load = () =>
    import("./Deck").then(
      ({ DeckApp }) => {
        setDeck({ Deck: DeckApp });
        setDoor("open");
      },
      () => setDoor("failed"),
    );
  // A server without the password, such as the local preview, answers anything but 401, and the deck loads.
  useEffect(() => {
    fetch("/api/deck/open").then(
      (response) => (response.status === 401 ? setDoor("locked") : load()),
      () => setDoor("failed"),
    );
  }, []);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    fetch("/api/deck/open", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) }).then(
      (response) => (response.ok ? load() : setDoor(response.status === 403 ? "wrong" : "failed")),
      () => setDoor("failed"),
    );
  };
  if (door === "open" && deck) return <deck.Deck view={view} />;
  if (door === "asking" || door === "open") return <main className="min-h-dvh bg-surface-2" />;
  const problem = door === "wrong" ? words.wrong : door === "failed" ? words.failed : null;
  return (
    <main className="flex min-h-dvh items-center justify-center bg-surface-2 p-6" data-deck="door">
      <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-4 rounded-md border border-line bg-surface p-6">
        <h1 className="text-h2 text-ink-heading">{words.title}</h1>
        <p className="text-body text-ink">{words.line}</p>
        <label htmlFor={id} className="text-small font-semibold text-ink">
          {words.label}
        </label>
        <input
          id={id}
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            if (door !== "locked") setDoor("locked");
          }}
          aria-invalid={door === "wrong" || undefined}
          aria-describedby={problem ? `${id}-problem` : undefined}
          className="h-11 rounded-sm border border-line-strong bg-surface px-3 text-body text-ink"
          data-door-password
        />
        {problem && (
          <p id={`${id}-problem`} role="alert" className="text-small text-error">
            {problem}
          </p>
        )}
        <Button variant="primary" type="submit">
          {words.open}
        </Button>
      </form>
    </main>
  );
}
