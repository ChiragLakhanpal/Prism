// A copy template with its {name} slots filled by elements, such as a number that explains itself
// or an ID in Roboto Mono: "Signed {date}, {days} days after its planned date." The words stay in
// the copy file, in one sentence a translator can read whole, and only the values are elements.
import { Fragment, type ReactNode } from "react";
import { copy } from "../copy";

export function Fill({ template, slots }: { template: string; slots: Record<string, ReactNode> }) {
  const parts = template.split(/\{(\w+)\}/);
  return (
    <>
      {parts.map((part, index) => (
        <Fragment key={index}>{index % 2 === 1 ? (slots[part] ?? `{${part}}`) : part}</Fragment>
      ))}
    </>
  );
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
