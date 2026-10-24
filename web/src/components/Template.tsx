// A copy template whose {name} slots hold nodes, such as a Num, so a sentence from the copy file
// can carry numbers that keep their form and their check. A slot with no value stays as written.
import { Fragment, type ReactNode } from "react";

export function Template({ text, values }: { text: string; values: Record<string, ReactNode> }) {
  const parts = text.split(/\{(\w+)\}/);
  return (
    <>
      {parts.map((part, index) =>
        index % 2 === 1 && part in values ? <Fragment key={index}>{values[part]}</Fragment> : <Fragment key={index}>{part}</Fragment>,
      )}
    </>
  );
}
