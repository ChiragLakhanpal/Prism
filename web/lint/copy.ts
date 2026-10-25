// The copy lint: the words DESIGN.md section 7 and GLOSSARY.md say Strata never writes.
// It checks one string at a time and returns a plain sentence for each problem it finds.
import { readFileSync } from "node:fs";
import { CAUSAL_WORDS, FIXED_TERMS, GLOSSARY_AVOID, REGION_CODES, WHAT_IF_WORDS } from "./rules.ts";

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&");

// Every form of a word: approve, approves, approved, approving; flag, flags, flagged, flagging.
function forms(word: string): string {
  const parts = word.split(/\s+/);
  const last = parts.pop()!;
  let ending: string;
  if (last.endsWith("e")) ending = `${escape(last.slice(0, -1))}(?:e|es|ed|ing)`;
  else if (/[^aeiou][aeiou][bcdfgklmnprstvz]$/i.test(last)) ending = `${escape(last)}(?:s|es|ed|ing|${escape(last.at(-1)!)}ed|${escape(last.at(-1)!)}ing)?`;
  else ending = `${escape(last)}(?:s|es|ed|ing)?`;
  return [...parts.map(escape), ending].join("\\s+");
}

type Rule = { pattern: RegExp; say: (found: string) => string };

// DESIGN.md section 7, rule 19: "Never write: approve, clear, ...; splitting." and "never "PP"".
function designRules(designPath: string): Rule[] {
  const text = readFileSync(designPath, "utf8");
  const rule = /\n19\. Never write: ([^\n]+)/.exec(text);
  if (!rule) throw new Error(`${designPath} has no rule 19 ("Never write: ...") in section 7.`);
  const list = rule[1].slice(0, rule[1].search(/\.\s+[A-Z]/));
  const words = list
    .replace(/\([^)]*\)/g, "")
    .split(/[;,]/)
    .map((word) => word.trim())
    .filter(Boolean);
  const never = [...rule[1].matchAll(/never "([^"]+)"/g)].map((match) => match[1]);
  return [
    ...words.map((word) => ({
      pattern: new RegExp(`\\b${forms(word)}\\b`, "gi"),
      say: (found: string) => `uses "${found}", a form of "${word}" that DESIGN.md section 7, rule 19 says never to write.`,
    })),
    ...never.map((word) => ({
      pattern: new RegExp(`\\b${escape(word)}s?\\b`, "g"),
      say: (found: string) => `uses "${found}". DESIGN.md section 7, rule 19 says to write the term in full.`,
    })),
  ];
}

const FIXED_RULES: Rule[] = [
  { pattern: /—/g, say: () => "has an em dash. DESIGN.md section 7, rule 3 says to use a period or a comma." },
  { pattern: /!/g, say: () => "has an exclamation mark. DESIGN.md section 7, rule 3 says never to use one." },
  { pattern: /[“”‘’]/g, say: (found) => `has a curly quote (${found}). Use straight quotes.` },
  {
    // In capitals too, and with any space between the words, such as a no-break space. A
    // lowercase bank, as in "the bank guarantee", is an ordinary word.
    pattern: /\b(?:[Tt]he|THE)\s+(?:Bank|BANK)\b/g,
    say: (found) => `uses "${found}". DESIGN.md section 7, rule 8 says "World Bank", except in a fixed term.`,
  },
  {
    pattern: new RegExp(`\\b(?:${REGION_CODES.join("|")})\\b`, "g"),
    say: (found) => `uses the region code "${found}". DESIGN.md section 7, rule 8 says to spell regions out.`,
  },
  ...GLOSSARY_AVOID.map(([word, instead]) => ({
    pattern: new RegExp(`\\b${forms(word)}\\b`, /^[A-Z]{2,}$/.test(word) ? "g" : "gi"),
    say: (found: string) => `uses "${found}", a form of "${word}", which GLOSSARY.md says to avoid. Write "${instead}".`,
  })),
];

// A link is "appeared together", never a cause (DESIGN.md section 7, rule 32): the causal words, in the copy
// blocks that write about links.
export function causalChecker(): CopyChecker {
  const pattern = new RegExp(`\\b(?:${CAUSAL_WORDS.map((word) => escape(word).replace(/ /g, "\\s+")).join("|")})\\b`, "gi");
  return (text) =>
    [...text.matchAll(pattern)].map(
      (match) => `uses "${match[0]}", which says a cause. DESIGN.md section 7, rule 32 says a link is written "appeared together".`,
    );
}

// A what-if says "went with", never a cause or a split (ticket 26): the words of WHAT_IF_WORDS, in the time
// estimate's copy blocks.
export function whatIfChecker(): CopyChecker {
  const pattern = new RegExp(`\\b(?:${WHAT_IF_WORDS.map(escape).join("|")})\\b`, "gi");
  return (text) =>
    [...text.matchAll(pattern)].map(
      (match) => `uses "${match[0]}". A what-if says comparable packages "went with" an approach (the 26 brief, section 7.4).`,
    );
}

export type CopyChecker = (text: string) => string[];

export function copyChecker(designPath: string): CopyChecker {
  const rules = [...designRules(designPath), ...FIXED_RULES];
  return (text) => {
    let rest = text;
    for (const term of FIXED_TERMS) rest = rest.replaceAll(term, " ");
    const problems: string[] = [];
    for (const rule of rules) {
      for (const match of rest.matchAll(rule.pattern)) problems.push(rule.say(match[0]));
    }
    return problems;
  };
}
