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
