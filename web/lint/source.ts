// Reads TypeScript and TSX with Vite's own parser and finds three things: the strings in a
// copy file, the strings a component renders without the copy file, and class names that
// step outside DESIGN.md's tokens or that the shell redesign retired.
import { parseAst } from "vite";
import {
  ARIA_TEXT_PROPS,
  DOM_TEXT_PROPERTIES,
  NON_COPY_PROPS,
  NON_COPY_SUFFIXES,
  RETIRED_CLASSES,
  SPACE_STEPS,
  STYLE_PROPS,
  UPPERCASE_ONLY_WITH,
} from "./rules.ts";

type Node = { type: string; start: number; end: number; [key: string]: unknown };

// where: what the component does with the text. from: the const that holds it, if any.
export type Found = { offset: number; text: string; where?: string; from?: string };

// Keys that hold types, not values. Strings in types are never shown to anyone.
const TYPE_KEYS = new Set(["typeAnnotation", "returnType", "typeParameters", "typeArguments", "superTypeArguments"]);
const TYPE_NODES = new Set(["TSTypeAliasDeclaration", "TSInterfaceDeclaration", "TSEnumDeclaration", "TSModuleDeclaration"]);

function walk(node: Node, visit: (node: Node, parent: Node | null, key: string) => boolean | void, parent: Node | null = null, key = "") {
  if (TYPE_NODES.has(node.type)) return;
  if (visit(node, parent, key) === false) return;
  for (const [childKey, value] of Object.entries(node)) {
    if (TYPE_KEYS.has(childKey)) continue;
    const children = Array.isArray(value) ? value : [value];
    for (const child of children) {
      if (child && typeof child === "object" && typeof (child as Node).type === "string") {
        walk(child as Node, visit, node, childKey);
      }
    }
  }
}

function parse(source: string, file: string): Node {
  return parseAst(source, { lang: file.endsWith(".tsx") ? "tsx" : "ts" }) as unknown as Node;
}

export function lineOf(source: string, offset: number): number {
  let line = 1;
  for (let i = 0; i < offset; i += 1) if (source.charCodeAt(i) === 10) line += 1;
  return line;
}

const isString = (node: Node) => node.type === "Literal" && typeof node.value === "string";

// Where each of these dotted paths sits in a copy file's exported copy object, as [start, end] offsets, such as
// "why" or "dataReadiness.server.fromNouns.connections" (ticket 22's causal-wording rule). A path the file does not
// have is left out.
export function scopedRanges(source: string, file: string, paths: string[]): [number, number][] {
  let root: Node | null = null;
  walk(parse(source, file), (node) => {
    if (root || node.type !== "VariableDeclarator" || (node.id as Node).type !== "Identifier" || (node.id as Node).name !== "copy") return;
    let init = node.init as Node | null;
    while (init && (init.type === "TSAsExpression" || init.type === "TSSatisfiesExpression")) init = init.expression as Node;
    if (init?.type === "ObjectExpression") root = init;
    return false;
  });
  const found: [number, number][] = [];
  for (const path of paths) {
    let at: Node | null = root;
    for (const part of path.split(".")) {
      let object: Node | null = at;
      while (object && (object.type === "TSAsExpression" || object.type === "TSSatisfiesExpression")) object = object.expression as Node;
      if (!object || object.type !== "ObjectExpression") {
        at = null;
        break;
      }
      const property = (object.properties as Node[]).find(
        (entry) => entry.type === "Property" && ((entry.key as Node).name === part || (entry.key as Node).value === part),
      );
      at = property ? (property.value as Node) : null;
    }
    if (at) found.push([at.start, at.end]);
  }
  return found;
}

// Every string a copy file holds: string literals, and the text between a template's slots.
// Object keys and import paths are names, not copy, so they are skipped.
export function copyStrings(source: string, file: string): Found[] {
  const found: Found[] = [];
  walk(parse(source, file), (node, parent, key) => {
    if (node.type === "ImportDeclaration" || (node.type === "ExportNamedDeclaration" && node.source)) return false;
    // A sentence split over lines with + is one string, so a fixed sentence still matches.
    const joined = concatenation(node);
    if (joined !== null) {
      found.push({ offset: node.start, text: joined });
      return false;
    }
    if (isString(node) && !(parent?.type === "Property" && key === "key" && !parent.computed)) {
      found.push({ offset: node.start, text: node.value as string });
    }
    if (node.type === "TemplateElement") {
      const value = node.value as { cooked: string | null; raw: string };
      found.push({ offset: node.start, text: value.cooked ?? value.raw });
    }
  });
  return found;
}

// "a" + "b" + "c" as one string, or null when the node is not a chain of string literals.
function concatenation(node: Node): string | null {
  if (node.type !== "BinaryExpression" || node.operator !== "+") return null;
  const side = (part: Node): string | null => (isString(part) ? (part.value as string) : concatenation(part));
  const left = side(node.left as Node);
  const right = side(node.right as Node);
  return left === null || right === null ? null : left + right;
}

// Every const, let or var in the file whose name a component might render, by name, with the
// value it starts with. A later assignment to a let is not followed. Scopes are ignored: a
// const and a parameter with the same name in two functions are read as one, which can only
// make the lint stricter.
function constants(root: Node): Map<string, Node> {
  const found = new Map<string, Node>();
  walk(root, (node) => {
    if (node.type !== "VariableDeclaration") return;
    for (const declarator of node.declarations as Node[]) {
      const id = declarator.id as Node;
      if (id.type === "Identifier" && declarator.init) found.set(id.name as string, declarator.init as Node);
    }
  });
  return found;
}

const hasWords = (text: string) => /\p{L}/u.test(text);

function propName(attribute: Node): string {
  const name = attribute.name as Node;
  return name.type === "JSXNamespacedName"
    ? `${(name.namespace as Node).name}:${(name.name as Node).name}`
    : (name.name as string);
}

// Whether a string given to this prop, or kept under this key, is read by a person.
function isCopyProp(name: string): boolean {
  if (name.startsWith("aria-")) return ARIA_TEXT_PROPS.has(name);
  if (NON_COPY_PROPS.has(name) || name.startsWith("data-")) return false;
  return !NON_COPY_SUFFIXES.some((suffix) => name.endsWith(suffix));
}

function keyName(property: Node): string | null {
  const key = property.key as Node;
  if (property.computed) return null;
  if (key.type === "Identifier") return key.name as string;
  if (key.type === "Literal") return String(key.value);
  return null;
}

// Text a component renders that is not from the copy file: words written in JSX, strings in
// JSX expressions, strings given to any prop that is not on NON_COPY_PROPS (inside objects
// and arrays too, each judged by its own key, and props passed with {...spread}), each piece
// of words joined with + ("Opened " + state), consts, lets and vars holding such strings that
// a component renders or passes by name, a key read from a local const object (words.empty or
// words["empty"]), a default prop value ({ body = "..." }), and a string written into the
// page outside JSX (document.title = "...", el.textContent = "..."). It follows one level of
// a lookup object (words.empty), not two (words.empty.title).
//
// It does not follow function calls, such as .map over a local array: RATIOS and BADGES in
// the gallery hold settings, and following them would flag those. Keep words in an array in
// the copy file, as copy.nav.tabs does.
export function literalText(source: string, file: string): Found[] {
  const root = parse(source, file);
  const consts = constants(root);

  // The strings an expression can end up as when it is rendered under the given prop or key
  // ("children" for text between tags). A function's arguments are not text, and neither is
  // anything a function returns.
  function strings(node: Node, prop: string, seen: Set<string> = new Set()): Found[] {
    if (STYLE_PROPS.has(prop)) return [];
    switch (node.type) {
      case "Literal":
        return isString(node) && isCopyProp(prop) ? [{ offset: node.start, text: node.value as string }] : [];
      case "TemplateLiteral": {
        const text = (node.quasis as Node[]).map((quasi) => (quasi.value as { raw: string }).raw).join("");
        return isCopyProp(prop) ? [{ offset: node.start, text }] : [];
      }
      case "JSXExpressionContainer":
      case "ParenthesizedExpression":
      case "TSAsExpression":
      case "TSSatisfiesExpression":
        return strings(node.expression as Node, prop, seen);
      case "ConditionalExpression":
        return [...strings(node.consequent as Node, prop, seen), ...strings(node.alternate as Node, prop, seen)];
      case "LogicalExpression":
        return [...strings(node.left as Node, prop, seen), ...strings(node.right as Node, prop, seen)];
      case "BinaryExpression": {
        // "Opened " + state or n + " packages": each piece is judged as the template form's
        // text is, and a chain of literals ("Something " + "went wrong.") as one string.
        if (node.operator !== "+") return [];
        const joined = concatenation(node);
        if (joined !== null) return isCopyProp(prop) ? [{ offset: node.start, text: joined }] : [];
        return [...strings(node.left as Node, prop, seen), ...strings(node.right as Node, prop, seen)];
      }
      case "ObjectExpression":
        return (node.properties as Node[]).flatMap((property) => {
          const key = property.type === "Property" ? keyName(property) : null;
          return key === null ? [] : strings(property.value as Node, key, seen);
        });
      case "ArrayExpression":
        return (node.elements as (Node | null)[]).flatMap((element) => (element ? strings(element, prop, seen) : []));
      case "Identifier": {
        const name = node.name as string;
        const init = consts.get(name);
        if (!init || seen.has(name)) return [];
        // Reported where the const is used, with the words it holds.
        return strings(init, prop, new Set([...seen, name])).map((found) => ({ ...found, offset: node.start, from: name }));
      }
      case "MemberExpression": {
        // words.empty or words["empty"], where words is a local const object: the value under
        // that key, judged by the key. A prop that is not copy, such as className={LOOK.box},
        // stops here.
        const object = node.object as Node;
        const property = node.property as Node;
        const key =
          !node.computed && property.type === "Identifier"
            ? (property.name as string)
            : node.computed && isString(property)
              ? (property.value as string)
              : null;
        if (key === null || object.type !== "Identifier" || !isCopyProp(prop)) return [];
        const name = object.name as string;
        const init = consts.get(name);
        if (!init || init.type !== "ObjectExpression" || seen.has(name)) return [];
        const held = (init.properties as Node[]).find((entry) => entry.type === "Property" && keyName(entry) === key);
        if (!held) return [];
        return strings(held.value as Node, key, new Set([...seen, name])).map((found) => ({
          ...found,
          offset: node.start,
          from: `${name}.${key}`,
        }));
      }
      default:
        return [];
    }
  }

  const found: Found[] = [];
  walk(root, (node, parent) => {
    // A default value in a destructured parameter, such as function A({ body = "..." }),
    // judged by its key.
    if (node.type === "AssignmentPattern" && parent?.type === "Property" && (node.right as Node).type !== "Identifier") {
      const key = keyName(parent);
      for (const text of key === null ? [] : strings(node.right as Node, key)) {
        if (hasWords(text.text)) found.push({ ...text, where: `defaults ${key} to` });
      }
    }
    if (node.type === "JSXText" && hasWords(node.value as string)) {
      found.push({ offset: node.start, text: (node.value as string).trim(), where: "renders" });
    }
    if (node.type === "JSXExpressionContainer" && (parent?.type === "JSXElement" || parent?.type === "JSXFragment")) {
      for (const text of strings(node.expression as Node, "children")) {
        if (hasWords(text.text)) found.push({ ...text, where: "renders" });
      }
    }
    if (node.type === "JSXAttribute" && node.value) {
      const prop = propName(node);
      for (const text of strings(node.value as Node, prop)) {
        if (hasWords(text.text)) found.push({ ...text, where: `passes ${prop}` });
      }
    }
    // {...{ title: "..." }} or {...props}: an object's strings, each judged by its own key.
    if (node.type === "JSXSpreadAttribute") {
      for (const text of strings(node.argument as Node, "children")) {
        if (hasWords(text.text)) found.push({ ...text, where: "spreads a prop with" });
      }
    }
    // document.title = "..." or el.textContent = "...": words written into the page directly.
    if (node.type === "AssignmentExpression" && (node.left as Node).type === "MemberExpression") {
      const target = node.left as Node;
      const property = target.property as Node;
      const name = !target.computed && property.type === "Identifier" ? (property.name as string) : null;
      if (name !== null && DOM_TEXT_PROPERTIES.has(name)) {
        for (const text of strings(node.right as Node, "children")) {
          if (hasWords(text.text)) found.push({ ...text, where: `writes ${name}` });
        }
      }
    }
  });
  return found;
}

// The words given to Term as literals, such as term="Comparable", so the gate can check each
// one against GLOSSARY.md before a renamed term breaks a screen.
export function termLiterals(source: string, file: string): Found[] {
  const found: Found[] = [];
  walk(parse(source, file), (node) => {
    if (node.type !== "JSXAttribute" || propName(node) !== "term" || !node.value) return;
    let value = node.value as Node;
    if (value.type === "JSXExpressionContainer") value = value.expression as Node;
    if (isString(value)) found.push({ offset: value.start, text: value.value as string });
  });
  return found;
}

const SPACING = /^-?(?:p[xytrblse]?|m[xytrblse]?|gap(?:-[xy])?|space-[xy])-(.+)$/;
const ALLOWED_STEPS = new Set(["0", "auto", ...SPACE_STEPS.map(String)]);

// Class names that leave DESIGN.md's tokens: a spacing step off the scale, an arbitrary
// spacing or font size, or an arbitrary color.
export function offTokenClasses(source: string, file: string): Found[] {
  const found: Found[] = [];
  walk(parse(source, file), (node) => {
    const text = isString(node)
      ? (node.value as string)
      : node.type === "TemplateElement"
        ? (node.value as { raw: string }).raw
        : null;
    if (text === null) return;
    for (const name of text.split(/\s+/)) {
      const utility = name.slice(name.lastIndexOf(":") + 1).replace(/^!/, "");
      const spacing = SPACING.exec(utility);
      const offScale = spacing && !ALLOWED_STEPS.has(spacing[1]);
      const arbitraryColor = /\[(?:#|rgb|hsl|oklch|color)/.test(utility);
      const arbitrarySize = /^text-\[\d/.test(utility);
      if (offScale || arbitraryColor || arbitrarySize) found.push({ offset: node.start, text: name });
    }
  });
  return found;
}

// The classes the shell redesign retired (ticket 90; DESIGN.md section 3): `uppercase` in a class string that does not
// also set the chart label's step, and the old title and box classes. `keeps` names those the file may still use, from
// FROZEN_CLASS_USES. Each found class is reported with what to use instead in `where`.
export function retiredClasses(source: string, file: string, keeps: readonly string[] = []): Found[] {
  const found: Found[] = [];
  walk(parse(source, file), (node) => {
    const text = isString(node)
      ? (node.value as string)
      : node.type === "TemplateElement"
        ? (node.value as { raw: string }).raw
        : null;
    if (text === null) return;
    const names = text.split(/\s+/).filter(Boolean);
    const utility = (name: string) => name.slice(name.lastIndexOf(":") + 1).replace(/^!/, "");
    const chartLabel = names.some((name) => utility(name) === UPPERCASE_ONLY_WITH);
    for (const name of names) {
      const used = utility(name);
      if (keeps.includes(used)) continue;
      if (used === "uppercase" && !chartLabel) found.push({ offset: node.start, text: name, where: UPPERCASE_ONLY_WITH });
      if (used in RETIRED_CLASSES) found.push({ offset: node.start, text: name, where: RETIRED_CLASSES[used] });
    }
  });
  return found;
}
