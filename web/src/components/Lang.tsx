// Lang: the one way text from a source or the writer gets its language attribute (the 42 design brief, section 4.2;
// DESIGN.md section 10). Who wrote a piece of text decides its language: the copy file writes English, the writer writes
// the working language, and a source keeps its own. The page is lang="en". Lang reads the language around it from
// context and sets lang on its element only when its own differs; null sets nothing, since the screen never guesses.
// Copy-file text inside text in another language, such as a citation marker, passes through Lang with "en", so a
// screen reader reads it in an English voice. A script written right to left also gets dir="rtl".
import { createContext, useContext, type ElementType, type ReactNode } from "react";

const Around = createContext("en");
// The languages written right to left among those a source can be written in (config/languages.toml's direction).
const RIGHT_TO_LEFT = new Set(["ar", "ur"]);

export function Lang({
  code,
  as: Tag = "span",
  children,
  className,
  id,
  ...rest
}: {
  code: string | null | undefined;
  as?: ElementType;
  children: ReactNode;
  className?: string;
  id?: string;
  [data: `data-${string}`]: string | number | boolean | undefined;
}) {
  const around = useContext(Around);
  const own = code ?? around;
  const differs = Boolean(code) && code !== around;
  return (
    <Tag id={id} lang={differs ? code : undefined} dir={differs && RIGHT_TO_LEFT.has(own) ? "rtl" : undefined} className={className} {...rest}>
      <Around.Provider value={own}>{children}</Around.Provider>
    </Tag>
  );
}

// The language around this point, for a component that must know it, such as the drawer's claim block.
export function useLanguageAround(): string {
  return useContext(Around);
}
