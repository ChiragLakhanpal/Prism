// Reads TypeScript and TSX with Vite's own parser and finds three things: the strings in a
// copy file, the strings a component renders without the copy file, and class names that
// step outside DESIGN.md's tokens.
import { parseAst } from "vite";
import { SPACE_STEPS, USER_FACING_PROPS } from "./rules.ts";

type Node = { type: string; start: number; end: number; [key: string]: unknown };

export type Found = { offset: number; text: string; where?: string };

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

// The strings an expression can end up as when it is rendered: a literal, a template, or
// either branch of a condition. Strings passed to a function are its arguments, not text.
function renderedStrings(node: Node): Found[] {
  switch (node.type) {
    case "Literal":
      return isString(node) ? [{ offset: node.start, text: node.value as string }] : [];
    case "TemplateLiteral":
      return [{ offset: node.start, text: (node.quasis as Node[]).map((quasi) => (quasi.value as { raw: string }).raw).join("") }];
    case "ConditionalExpression":
      return [...renderedStrings(node.consequent as Node), ...renderedStrings(node.alternate as Node)];
    case "LogicalExpression":
      return [...renderedStrings(node.left as Node), ...renderedStrings(node.right as Node)];
    case "ParenthesizedExpression":
    case "TSAsExpression":
    case "TSSatisfiesExpression":
      return renderedStrings(node.expression as Node);
    default:
      return [];
  }
}

const hasWords = (text: string) => /\p{L}/u.test(text);

function propName(attribute: Node): string {
  const name = attribute.name as Node;
  return name.type === "JSXNamespacedName"
    ? `${(name.namespace as Node).name}:${(name.name as Node).name}`
    : (name.name as string);
}

// Text a component renders that is not from the copy file: words written in JSX, and literal
// strings given to a prop a person reads or hears (USER_FACING_PROPS).
export function literalText(source: string, file: string): Found[] {
  const found: Found[] = [];
  walk(parse(source, file), (node, parent) => {
    if (node.type === "JSXText" && hasWords(node.value as string)) {
      found.push({ offset: node.start, text: (node.value as string).trim(), where: "renders" });
    }
    if (node.type === "JSXExpressionContainer" && (parent?.type === "JSXElement" || parent?.type === "JSXFragment")) {
      for (const text of renderedStrings(node.expression as Node)) {
        if (hasWords(text.text)) found.push({ ...text, where: "renders" });
      }
    }
    if (node.type === "JSXAttribute" && node.value && USER_FACING_PROPS.has(propName(node))) {
      const value = node.value as Node;
      const strings = value.type === "JSXExpressionContainer" ? renderedStrings(value.expression as Node) : renderedStrings(value);
      for (const text of strings) {
        if (hasWords(text.text)) found.push({ ...text, where: `passes ${propName(node)}` });
      }
    }
  });
  return found;
}

const SPACING = /^-?(?:p[xytrblse]?|m[xytrblse]?|gap(?:-[xy])?|space-[xy])-(.+)$/;
const ALLOWED_STEPS = new Set(["0", "auto", ...SPACE_STEPS.map(String)]);

// Class names that leave DESIGN.md's tokens: a spacing step off the scale, an arbitrary
// spacing or font size, or an arbitrary colour.
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
      const arbitraryColour = /\[(?:#|rgb|hsl|oklch|color)/.test(utility);
      const arbitrarySize = /^text-\[\d/.test(utility);
      if (offScale || arbitraryColour || arbitrarySize) found.push({ offset: node.start, text: name });
    }
  });
  return found;
}
