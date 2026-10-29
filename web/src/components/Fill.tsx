// A copy template with its {name} slots filled by elements, such as a number that explains itself
// or an ID in Roboto Mono: "Signed {date}, {days} days after its planned date." The words stay in
// the copy file, in one sentence a translator can read whole, and only the values are elements.
//
// A number you can press is an inline-flex button, after which a browser may break the line, so a line could start
// with the full stop after it, or a "months" the copy binds to it with a no-break space would drop to the next line.
// So a Num slot and what follows it up to the next plain space (its punctuation, or a no-break space and the words it
// binds, as in "{plan}\u00a0months.") sit in one span that does not wrap (block 9; ticket 101's design review). Only a
// Num: a long slot, such as a project's name, must keep its own line breaks.
import { Fragment, isValidElement, type ReactNode } from "react";
import { copy } from "../copy";
import { Num } from "./Num";

const KEPT_WITH_NUMBER = /^(?:\u00a0[^ \t\n]+|[.,;:?)%]+)/;

export function Fill({ template, slots }: { template: string; slots: Record<string, ReactNode> }) {
  const parts = template.split(/\{(\w+)\}/);
  const out: ReactNode[] = [];
  for (let index = 0; index < parts.length; index++) {
    if (index % 2 === 0) {
      out.push(<Fragment key={index}>{parts[index]}</Fragment>);
      continue;
    }
    const slot = slots[parts[index]] ?? `{${parts[index]}}`;
    const next = parts[index + 1] ?? "";
    const kept = isValidElement(slot) && slot.type === Num ? KEPT_WITH_NUMBER.exec(next)?.[0] : undefined;
    if (kept) {
      out.push(
        <span key={index} className="whitespace-nowrap">
          {slot}
          {kept}
        </span>,
      );
      parts[index + 1] = next.slice(kept.length);
    } else {
      out.push(<Fragment key={index}>{slot}</Fragment>);
    }
  }
  return <>{out}</>;
}

// Items in a sentence: "A", "A and B", or "A, B and C", with no serial comma.
export function Joined({ items }: { items: ReactNode[] }) {
  return (
    <>
      {items.map((item, index) => (
        <Fragment key={index}>
          {index > 0 && (index === items.length - 1 ? copy.list.and : copy.list.comma)}
          {item}
        </Fragment>
      ))}
    </>
  );
}

// Words such as "re-dated" and "re-estimated" kept whole on one line: a browser may break a line after a
// hyphen, which reads as "re- / dated" (the 21 design review, round 2, F5). Each word with a hyphen inside
// sits in a span that does not wrap. The non-breaking hyphen would do the same, but Open Sans's Latin subset
// has no glyph for it, so it would draw from another font.
export function Unbroken({ text }: { text: string }) {
  const parts = text.split(/([A-Za-z]+-[A-Za-z]+)/);
  return (
    <>
      {parts.map((part, index) => (index % 2 === 1 ? <span key={index} className="whitespace-nowrap">{part}</span> : <Fragment key={index}>{part}</Fragment>))}
    </>
  );
}
